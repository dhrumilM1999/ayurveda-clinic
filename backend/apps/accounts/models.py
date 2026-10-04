"""
Staff users, roles, per-branch role assignments, doctor schedules and login OTPs.
ASK FIRST before changing these models (it changes the database).
"""
import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.models import BranchScopedModel, OrgScopedModel
from apps.organizations.models import LANGUAGE_CHOICES


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

    def create_user(self, username, password=None, **extra):
        if not username:
            raise ValueError("Username is required")
        user = self.model(username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """A staff member who can log in (doctor, receptionist, ...)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="users",
    )
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True, help_text="Used for login OTP")
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    designation = models.CharField(max_length=100, blank=True)
    # Doctor details
    is_doctor = models.BooleanField(default=False, help_text="Shows in doctor lists and schedules")
    qualification = models.CharField(max_length=200, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    # Access
    is_org_admin = models.BooleanField(default=False, help_text="Can see and manage all branches")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text="Can open the Django admin site")
    # Housekeeping
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()
    all_objects = models.Manager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name or self.username

    def delete(self, using=None, keep_parents=False, user=None):
        """Soft delete: the user can no longer log in, but history keeps their name."""
        self.is_deleted = True
        self.is_active = False
        self.deleted_at = timezone.now()
        self.updated_by = user
        self.save(update_fields=["is_deleted", "is_active", "deleted_at", "updated_by", "updated_at"])


class Role(OrgScopedModel):
    """A named set of permission codes (see permissions_catalog.py). Editable by admins."""

    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=50)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.JSONField(default=list, blank=True)
    requires_2fa = models.BooleanField(default=False, help_text="Ask for an OTP at login")
    is_system = models.BooleanField(default=False, help_text="Created automatically; cannot be deleted")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], condition=Q(is_deleted=False), name="uniq_role_code_per_org"
            )
        ]

    def __str__(self):
        return self.name


class UserBranchRole(OrgScopedModel):
    """Which role a user has in which branch. One role per user per branch."""

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="branch_roles")
    branch = models.ForeignKey("organizations.Branch", on_delete=models.PROTECT, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "branch"], condition=Q(is_deleted=False), name="uniq_role_per_user_branch"
            )
        ]

    def __str__(self):
        return f"{self.user} @ {self.branch}: {self.role}"


WEEKDAY_CHOICES = [
    (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
    (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
]


class DoctorSchedule(BranchScopedModel):
    """When a doctor sits in a branch, e.g. Monday 10:00-13:00, 15-minute slots."""

    doctor = models.ForeignKey(User, on_delete=models.PROTECT, related_name="schedules")
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_minutes = models.PositiveSmallIntegerField(default=15)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["weekday", "start_time"]

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")

    def __str__(self):
        return f"{self.doctor} {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class LoginChallenge(models.Model):
    """A one-time password (OTP) sent during login. Only a hash of the code is stored."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_challenges")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)

    def is_usable(self) -> bool:
        return (
            self.used_at is None
            and self.expires_at > timezone.now()
            and self.attempts < settings.OTP_MAX_ATTEMPTS
        )
