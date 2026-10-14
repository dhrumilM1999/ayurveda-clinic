from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.common.models import MasterValue
from apps.common.viewsets import AuditedModelViewSet
from apps.organizations.models import Branch
from apps.organizations.services import organization_features
from apps.organizations.views import PublicBrandingView

from .models import Enquiry, STATUS_CHOICES
from .serializers import EnquirySerializer, PublicEnquirySerializer

FEATURE = "online_enquiry"
# Common reasons shown as quick choices on the public form (clinic dropdown values: Settings -> master "complaint")
FALLBACK_CONCERNS = ["Joint pain", "Acidity / digestion", "Skin problem", "Headache / migraine", "Weight loss",
                     "Women's health", "Panchakarma", "General check-up"]


def allowed_origin(request) -> str:
    """The website address that may call the public form from the browser (ENQUIRY_ALLOWED_ORIGINS in .env)."""
    origin = request.headers.get("Origin", "")
    return origin if origin and origin in settings.ENQUIRY_ALLOWED_ORIGINS else ""


class PublicCors:
    """Lets the clinic's own website (listed in .env) post the form. Everybody else is blocked by the browser."""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        origin = allowed_origin(request)
        if origin:
            response["Access-Control-Allow-Origin"] = origin
            response["Vary"] = "Origin"
            response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    def options(self, request, *args, **kwargs):
        return Response(status=http.HTTP_204_NO_CONTENT)


def _clinic():
    org = PublicBrandingView.clinic()
    if org is None or not organization_features(org.id).get(FEATURE):
        return None
    return org


class PublicEnquiryFormView(PublicCors, APIView):
    """GET /public/enquiry-form/ - what the public form needs: clinic name, branches, quick concerns."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        org = PublicBrandingView.clinic()
        if org is None or not organization_features(org.id).get(FEATURE):
            return Response({"enabled": False, "clinic": org.name if org else ""})
        branches = Branch.objects.filter(organization=org, is_active=True, is_deleted=False).order_by("created_at")
        concerns = list(MasterValue.objects.filter(organization=org, category="complaint", is_active=True)
                        .order_by("sort_order").values_list("label", flat=True)[:12]) or FALLBACK_CONCERNS
        return Response({
            "enabled": True, "clinic": org.name, "has_logo": bool(org.logo),
            "phone": org.phone, "multi_branch": org.multi_branch,
            "branches": [{"id": str(b.id), "name": b.name, "city": b.city} for b in branches],
            "concerns": concerns,
        })


class PublicEnquiryView(PublicCors, APIView):
    """POST /public/enquiries/ - a visitor of the clinic website asks for an appointment or information."""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "enquiry"

    def post(self, request):
        org = _clinic()
        if org is None:
            return Response({"detail": "Online enquiries are not accepted right now."}, status=http.HTTP_404_NOT_FOUND)
        serializer = PublicEnquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if data.pop("website", ""):  # a bot filled the hidden field: pretend everything is fine
            return Response({"ok": True}, status=http.HTTP_201_CREATED)
        branch = data.pop("branch", None)
        if branch is not None and (branch.organization_id != org.id or not branch.is_active):
            branch = None
        # The same number asking again within 10 minutes is one enquiry, not two
        recent = Enquiry.objects.filter(organization=org, phone=data["phone"], source="website",
                                        created_at__gte=timezone.now() - timedelta(minutes=10)).exists()
        if not recent:
            Enquiry.objects.create(
                organization=org, branch=branch, source="website", ip_address=_ip(request),
                user_agent=request.headers.get("User-Agent", "")[:200], **data)
        return Response({"ok": True}, status=http.HTTP_201_CREATED)


def _ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",")[0].strip() or request.META.get("REMOTE_ADDR") or None) or None


class EnquiryViewSet(AuditedModelViewSet):
    """
    The front desk's list of enquiries (Online enquiry screen).
    GET /enquiries/?status=new&q=   PATCH /enquiries/<id>/ (status, notes, follow-up date, linked patient)
    POST /enquiries/ records a phone or walk-in enquiry.   GET /enquiries/summary/ counts for the menu badge.
    """

    queryset = Enquiry.objects.select_related("branch", "assigned_to", "patient")
    serializer_class = EnquirySerializer
    permission_prefix = "enquiries"
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["status", "source", "assigned_to"]
    search_fields = ["name", "phone", "message", "concern"]
    ordering_fields = ["created_at", "preferred_date", "status"]
    required_permissions = {"summary": "enquiries.view"}

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        from apps.organizations.services import is_feature_enabled

        branch = getattr(request, "branch", None)
        if branch is not None and not is_feature_enabled(branch, FEATURE):
            raise PermissionDenied("Online enquiries are switched off. Switch them on in Additional settings.")

    def perform_create(self, serializer):
        # A phone / walk-in enquiry is recorded by staff; the visitor's consent is theirs to give on the call
        serializer.validated_data.setdefault("source", "phone")
        super().perform_create(serializer)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        counts = dict(self.get_queryset().values_list("status").annotate(n=Count("id")))
        today = timezone.localdate()
        return Response({
            "new": counts.get("new", 0), "total": sum(counts.values()),
            "follow_up_due": self.get_queryset().filter(follow_up_on__lte=today).exclude(status__in=["appointment", "not_interested", "closed"]).count(),
            "by_status": {code: counts.get(code, 0) for code, _ in STATUS_CHOICES},
        })
