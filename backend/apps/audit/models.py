"""
The audit log: who did what, when, from where. APPEND-ONLY — rows can never be
changed or deleted (blocked here in Python and, on PostgreSQL, by a database trigger).
ASK FIRST before editing.
"""
import uuid

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class AuditLogQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise PermissionError("Audit logs cannot be changed.")

    def delete(self):
        raise PermissionError("Audit logs cannot be deleted.")


class AuditLog(models.Model):
    ACTIONS = [
        ("view", "Viewed"),
        ("create", "Created"),
        ("update", "Changed"),
        ("delete", "Deleted"),
        ("print", "Printed"),
        ("export", "Exported"),
        ("share", "Shared"),
        ("login", "Logged in"),
        ("login_failed", "Login failed"),
        ("otp_sent", "OTP sent"),
        ("otp_failed", "OTP failed"),
        ("logout", "Logged out"),
        ("password_change", "Password changed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    branch = models.ForeignKey(
        "organizations.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    username = models.CharField(max_length=150, blank=True, help_text="Kept even if the user is removed")
    action = models.CharField(max_length=20, choices=ACTIONS, db_index=True)
    object_type = models.CharField(max_length=100, blank=True, db_index=True)
    object_id = models.CharField(max_length=64, blank=True, db_index=True)
    object_repr = models.CharField(max_length=255, blank=True)
    changes = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["organization", "created_at"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Audit logs cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit logs cannot be deleted.")

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.username} {self.action} {self.object_type}"


class ErrorLog(models.Model):
    """
    A mistake or crash seen by a user: a server error, a refused action, a screen that broke, a lost connection.
    The same problem happening again is counted on one line (count, last_seen) instead of filling the list.
    The owner reads these on the Error log screen. Nothing here is a patient record: no typed text is stored,
    only what went wrong, where, and who it happened to. ASK FIRST before editing.
    """

    SOURCES = [("backend", "Server"), ("frontend", "Screen")]
    LEVELS = [("error", "Error"), ("warning", "Warning"), ("notice", "Notice")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_seen = models.DateTimeField(db_index=True)
    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    branch = models.ForeignKey(
        "organizations.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    username = models.CharField(max_length=150, blank=True)
    session_id = models.CharField(max_length=40, blank=True, db_index=True, help_text="One login = one session")
    request_code = models.CharField(max_length=12, db_index=True, help_text="Short code the user can read out")
    source = models.CharField(max_length=10, choices=SOURCES, db_index=True)
    level = models.CharField(max_length=10, choices=LEVELS, db_index=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    method = models.CharField(max_length=10, blank=True)
    path = models.CharField(max_length=255, blank=True, help_text="API address, without the part after ?")
    screen = models.CharField(max_length=255, blank=True, help_text="Page the user was on")
    message = models.TextField(blank=True)
    details = models.TextField(blank=True, help_text="Technical detail: server traceback or browser stack")
    trail = models.JSONField(default=list, blank=True, help_text="The last steps the user took before this")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    fingerprint = models.CharField(max_length=40, db_index=True)
    count = models.PositiveIntegerField(default=1)
    is_resolved = models.BooleanField(default=False, db_index=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+",
    )
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["-last_seen"]
        indexes = [models.Index(fields=["organization", "last_seen"]), models.Index(fields=["organization", "is_resolved", "level"])]

    def __str__(self):
        return f"{self.last_seen:%Y-%m-%d %H:%M} {self.level} {self.message[:60]}"
