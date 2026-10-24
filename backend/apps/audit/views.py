from datetime import timedelta

import django_filters
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.accounts.permissions import BranchPermission, resolve_request_branch

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


# --- Error log -------------------------------------------------------------------------------
from django.db.models import Sum  # noqa: E402
from django.utils import timezone  # noqa: E402
from rest_framework import mixins  # noqa: E402
from rest_framework.decorators import action  # noqa: E402
from rest_framework.response import Response  # noqa: E402
from rest_framework.throttling import UserRateThrottle  # noqa: E402
from rest_framework.views import APIView  # noqa: E402

from .error_log import _clean_trail, record_error, session_id_of  # noqa: E402
from .models import ErrorLog  # noqa: E402


class ErrorLogSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", default="", read_only=True)
    resolved_by_name = serializers.CharField(source="resolved_by.username", default="", read_only=True)

    class Meta:
        model = ErrorLog
        fields = [
            "id", "created_at", "last_seen", "branch", "branch_name", "user", "username", "session_id", "request_code",
            "source", "level", "status_code", "method", "path", "screen", "message", "count",
            "is_resolved", "resolved_at", "resolved_by_name", "note",
        ]
        read_only_fields = [f for f in fields if f not in ("is_resolved", "note")]


class ErrorLogDetailSerializer(ErrorLogSerializer):
    class Meta(ErrorLogSerializer.Meta):
        fields = ErrorLogSerializer.Meta.fields + ["details", "trail", "ip_address", "user_agent"]
        read_only_fields = [f for f in fields if f not in ("is_resolved", "note")]


class ErrorLogFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(field_name="last_seen", lookup_expr="date__gte")
    date_to = django_filters.DateFilter(field_name="last_seen", lookup_expr="date__lte")

    class Meta:
        model = ErrorLog
        fields = ["level", "source", "is_resolved", "user", "session_id", "branch", "request_code"]


class ErrorLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """
    The Error log: what went wrong, for whom, where. Org admins see all branches; others only the current one.
    The only things that can be changed are "resolved" and a note (never deleted).
    """

    permission_classes = [IsAuthenticated, BranchPermission]
    required_permissions = {"list": "audit.view", "retrieve": "audit.view", "partial_update": "audit.view",
                            "update": "audit.view", "summary": "audit.view"}
    branch_scoped = True
    filterset_class = ErrorLogFilter
    search_fields = ["username", "message", "path", "screen", "request_code"]
    ordering_fields = ["last_seen", "created_at", "count"]
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        return ErrorLogDetailSerializer if self.action in ("retrieve", "partial_update") else ErrorLogSerializer

    def get_queryset(self):
        user = self.request.user
        qs = ErrorLog.objects.filter(organization_id=user.organization_id).select_related("branch", "resolved_by")
        if not user.is_org_admin:
            qs = qs.filter(branch=self.request.branch)
        return qs

    def perform_update(self, serializer):
        resolved = serializer.validated_data.get("is_resolved")
        extra = {}
        if resolved is True and not serializer.instance.is_resolved:
            extra = {"resolved_at": timezone.now(), "resolved_by": self.request.user}
        elif resolved is False:
            extra = {"resolved_at": None, "resolved_by": None}
        serializer.save(**extra)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Numbers for the top of the screen: still open, by level, and the last 24 hours."""
        open_rows = self.get_queryset().filter(is_resolved=False)
        since = timezone.now() - timedelta(hours=24)
        return Response({
            "open_errors": open_rows.filter(level="error").count(),
            "open_warnings": open_rows.filter(level="warning").count(),
            "open_notices": open_rows.filter(level="notice").count(),
            "last_24h": open_rows.filter(last_seen__gte=since).aggregate(n=Sum("count"))["n"] or 0,
        })


class ErrorReportThrottle(UserRateThrottle):
    scope = "error_report"


class ErrorReportSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["js", "react", "network", "api", "trail"], default="js")
    message = serializers.CharField(max_length=1000, allow_blank=True, required=False, default="")
    details = serializers.CharField(max_length=20000, allow_blank=True, required=False, default="")
    screen = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    path = serializers.CharField(max_length=255, allow_blank=True, required=False, default="")
    method = serializers.CharField(max_length=10, allow_blank=True, required=False, default="")
    status_code = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=599)
    code = serializers.CharField(max_length=12, allow_blank=True, required=False, default="")
    trail = serializers.ListField(child=serializers.DictField(), max_length=60, required=False, default=list)


class ErrorReportView(APIView):
    """
    The screen tells the server it broke: POST /error-logs/report/
    {kind: js|react|network|api|trail, message, details, screen, path, method, status_code, trail, code}
    kind "trail" with a "code" only adds the user's last steps to a server error already written under that code.
    """

    throttle_classes = [ErrorReportThrottle]

    def post(self, request):
        ser = ErrorReportSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            request.branch = resolve_request_branch(request)
        except Exception:  # noqa: BLE001 - a wrong branch header must not hide the report
            request.branch = None
        if d["kind"] == "trail":
            row = ErrorLog.objects.filter(request_code=d["code"], user=request.user).first()
            if row is not None and not row.trail:
                row.trail = _clean_trail(d["trail"])
                row.screen = row.screen or d["screen"]
                row.save(update_fields=["trail", "screen"])
            return Response({"code": d["code"]})
        code = record_error(
            request, source="frontend", level="error", status_code=d.get("status_code"), method=d["method"], path=d["path"],
            message=d["message"] or d["kind"], details=d["details"], screen=d["screen"], trail=d["trail"],
            session_id=session_id_of(request),
        )
        return Response({"code": code}, status=201)
