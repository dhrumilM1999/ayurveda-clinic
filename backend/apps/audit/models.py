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
