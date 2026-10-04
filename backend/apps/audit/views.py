import django_filters
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import BranchPermission

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", default="", read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            "id", "created_at", "branch", "branch_name", "user", "username", "action",
            "object_type", "object_id", "object_repr", "changes", "ip_address", "user_agent",
        ]


class AuditLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="created_at", lookup_expr="date__lte")

    class Meta:
        model = AuditLog
        fields = ["action", "user", "branch", "object_type", "object_id"]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only list of the audit log. Org admins see all branches; others only the current one."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    required_permissions = {"list": "audit.view", "retrieve": "audit.view"}
    # A branch must be chosen; the user needs audit.view in it.
    branch_scoped = True
    filterset_class = AuditLogFilter
    search_fields = ["username", "object_repr", "object_type"]
    ordering_fields = ["created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = AuditLog.objects.filter(organization_id=user.organization_id).select_related("branch")
        if not user.is_org_admin:
            qs = qs.filter(branch=self.request.branch)
        return qs
