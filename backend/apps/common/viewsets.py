"""
Shared API view classes. They take care of, for every module:
- only showing rows of the user's organization (and current branch, if branch_scoped),
- checking the permission code for the action,
- filling created_by / updated_by,
- soft delete instead of real delete,
- writing an audit log entry for create / update / delete.
"""
from django.db import models
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import BranchPermission
from apps.audit.services import log_action

HIDDEN_FIELDS = {"password"}


def snapshot(instance, field_names):
    """Plain values of some fields, used to record what changed."""
    data = {}
    for name in field_names:
        if name in HIDDEN_FIELDS:
            continue
        try:
            field = instance._meta.get_field(name)
        except Exception:
            continue
        if not getattr(field, "concrete", False) or isinstance(field, models.ManyToManyField):
            continue
        value = getattr(instance, field.attname, None)
        data[name] = value if isinstance(value, (str, int, float, bool, list, dict, type(None))) else str(value)
    return data


class AuditedModelViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, BranchPermission]
    # e.g. "rooms" -> needs "rooms.view" to read and "rooms.manage" to change
    permission_prefix: str | None = None
    # Optional exact codes per action, e.g. {"set_password": "staff.manage"}
    required_permissions: dict[str, str] = {}
    # True = needs the X-Branch-ID header and only shows that branch's rows
    branch_scoped = False
    # True = needs the X-Branch-ID header (permission checked in that branch) but shows
    # organization-wide rows, e.g. patients
    branch_required = False
    # Fields whose content must never be copied into the audit log (only "changed" is recorded)
    audit_redact_fields: set[str] = set()

    def _redact(self, data):
        return {k: ("[hidden]" if k in self.audit_redact_fields and v else v) for k, v in data.items()}

    def get_queryset(self):
        qs = super().get_queryset().filter(organization_id=self.request.user.organization_id)
        if self.branch_scoped:
            qs = qs.filter(branch=self.request.branch)
        return qs

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["branch"] = getattr(self.request, "branch", None)
        return context

    def perform_create(self, serializer):
        user = self.request.user
        extra = {"organization_id": user.organization_id, "created_by": user, "updated_by": user}
        if self.branch_scoped:
            extra["branch"] = self.request.branch
        instance = serializer.save(**extra)
        log_action(
            self.request, "create", instance,
            changes={"after": self._redact(snapshot(instance, serializer.validated_data.keys()))},
        )

    def perform_update(self, serializer):
        fields = list(serializer.validated_data.keys())
        before = snapshot(serializer.instance, fields)
        instance = serializer.save(updated_by=self.request.user)
        after = snapshot(instance, fields)
        changed = {
            k: ({"from": before.get(k), "to": after.get(k)} if k not in self.audit_redact_fields else "changed")
            for k in after if before.get(k) != after.get(k)
        }
        if changed:
            log_action(self.request, "update", instance, changes=changed)

    def perform_destroy(self, instance):
        instance.delete(user=self.request.user)
        log_action(self.request, "delete", instance)
