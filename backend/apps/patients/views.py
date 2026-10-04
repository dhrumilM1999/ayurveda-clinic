import re

from django.db.models import Count, Q
from django.http import FileResponse
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.audit.views import AuditLogSerializer
from apps.common.viewsets import AuditedModelViewSet

from .models import ConsentPurpose, Patient, PatientConsent, PatientDocument, PatientVital
from .serializers import (
    MEDICAL_TEXT, ConsentPurposeSerializer, ConsentSerializer, DocumentSerializer, DuplicateSerializer,
    PatientListSerializer, PatientSerializer, VitalSerializer,
)
from .services import IMAGE_TYPES, check_upload, current_consents


def patient_or_404(request, patient_id):
    patient = Patient.objects.filter(organization_id=request.user.organization_id, pk=patient_id).first()
    if patient is None:
        raise NotFound("Patient not found.")
    return patient


def required_patient_param(request):
    patient_id = request.query_params.get("patient")
    if not patient_id:
        raise ValidationError({"patient": "Choose a patient (?patient=<id>)."})
    return patient_or_404(request, patient_id)


class PatientViewSet(AuditedModelViewSet):
    """Patients (organization-wide). Patients are never deleted."""

    queryset = Patient.objects.select_related(
        "title", "blood_group", "marital_status", "referral_source", "emergency_relation",
        "registered_branch", "created_by",
    )
    serializer_class = PatientSerializer
    branch_required = True
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    audit_redact_fields = set(MEDICAL_TEXT)
    filterset_fields = ["gender", "registered_branch", "is_vip", "is_foc"]
    ordering_fields = ["created_at", "first_name", "uhid", "registration_date"]
    required_permissions = {
        "list": "patients.view",
        "retrieve": "patients.view",
        "create": "patients.create",
        "update": "patients.edit",
        "partial_update": "patients.edit",
        "duplicates": ("patients.create", "patients.view"),
        "photo": "patients.view",
        "upload_photo": ("patients.edit", "patients.create"),
        "activity": "audit.view",
    }

    def get_serializer_class(self):
        return PatientListSerializer if self.action == "list" else PatientSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            qs = qs.annotate(allergy_count=Count("allergies", filter=Q(allergies__is_deleted=False))).order_by("-created_at")
            search = self.request.query_params.get("q", "").strip()
            if search:
                qs = qs.filter(self._search_filter(search))
            date_from = self.request.query_params.get("date_from")
            date_to = self.request.query_params.get("date_to")
            if date_from:
                qs = qs.filter(registration_date__gte=date_from)
            if date_to:
                qs = qs.filter(registration_date__lte=date_to)
        return qs

    @staticmethod
    def _search_filter(search):
        """Search by patient ID, mobile number or name (all words must match)."""
        digits = re.sub(r"\D", "", search)
        if digits and len(digits) >= 4 and len(digits) == len(re.sub(r"[\s+\-]", "", search)):
            return Q(mobile__contains=digits) | Q(alternate_mobile__contains=digits) | Q(uhid__icontains=search)
        condition = Q(uhid__icontains=search)
        words = Q()
        for word in search.split():
            words &= Q(first_name__icontains=word) | Q(middle_name__icontains=word) | Q(last_name__icontains=word)
        return condition | words

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        search = request.query_params.get("q", "").strip()
        if search:
            log_action(request, "view", object_type="patients.search", object_repr=f"Search: {search}"[:255],
                       changes={"search": search, "results": response.data.get("count")})
        return response

    def retrieve(self, request, *args, **kwargs):
        patient = self.get_object()
        log_action(request, "view", patient)
        return Response(self.get_serializer(patient).data)

    @action(detail=False, methods=["get"])
    def duplicates(self, request):
        """Patients who may be the same person (same mobile, or same name). Used while registering."""
        mobile = re.sub(r"\D", "", request.query_params.get("mobile", ""))[-10:]
        first = request.query_params.get("first_name", "").strip()
        last = request.query_params.get("last_name", "").strip()
        condition = Q()
        if len(mobile) == 10:
            condition |= Q(mobile=mobile) | Q(alternate_mobile=mobile)
        if first and last:
            condition |= Q(first_name__iexact=first, last_name__iexact=last)
        if not condition:
            return Response([])
        exclude = request.query_params.get("exclude")
        qs = Patient.objects.filter(condition, organization_id=request.user.organization_id)
        if exclude:
            qs = qs.exclude(pk=exclude)
        return Response(DuplicateSerializer(qs[:10], many=True).data)

    @action(detail=True, methods=["get"])
    def photo(self, request, pk=None):
        patient = self.get_object()
        if not patient.photo:
            raise NotFound("No photo.")
        return FileResponse(patient.photo.open("rb"), content_type="image/jpeg")

    @photo.mapping.post
    def upload_photo(self, request, pk=None):
        patient = self.get_object()
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "Choose a photo."})
        check_upload(uploaded, IMAGE_TYPES)
        patient.photo.save(uploaded.name, uploaded, save=False)
        patient.updated_by = request.user
        patient.save(update_fields=["photo", "updated_by", "updated_at"])
        log_action(request, "update", patient, changes={"photo": "changed"})
        return Response({"has_photo": True})

    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        """Who viewed or changed this patient's record (from the audit log)."""
        patient = self.get_object()
        logs = AuditLog.objects.filter(
            Q(object_id=str(patient.pk)) | Q(changes__patient=str(patient.pk)),
            organization_id=request.user.organization_id,
        ).select_related("branch")[:200]
        return Response(AuditLogSerializer(logs, many=True).data)


class VitalViewSet(AuditedModelViewSet):
    """Vitals of one patient (?patient=<id>). Corrections: remove and add again."""

    queryset = PatientVital.objects.select_related("branch", "created_by")
    serializer_class = VitalSerializer
    branch_required = True
    pagination_class = None
    http_method_names = ["get", "post", "delete", "head", "options"]
    required_permissions = {
        "list": ("emr.view", "patients.vitals"),
        "retrieve": ("emr.view", "patients.vitals"),
        "create": "patients.vitals",
        "destroy": ("emr.edit", "patients.vitals"),
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            qs = qs.filter(patient=required_patient_param(self.request))
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        instance = serializer.save(
            organization_id=user.organization_id, branch=self.request.branch, created_by=user, updated_by=user,
            recorded_at=serializer.validated_data.get("recorded_at") or timezone.now(),
        )
        log_action(self.request, "create", instance)


class DocumentViewSet(AuditedModelViewSet):
    """Uploaded reports and files of one patient (?patient=<id>)."""

    queryset = PatientDocument.objects.select_related("document_type", "branch", "created_by")
    serializer_class = DocumentSerializer
    branch_required = True
    pagination_class = None
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "delete", "head", "options"]
    required_permissions = {
        "list": "emr.view",
        "retrieve": "emr.view",
        "file": "emr.view",
        "create": ("patients.edit", "patients.create", "emr.edit"),
        "destroy": "emr.edit",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            qs = qs.filter(patient=required_patient_param(self.request))
        return qs

    def perform_create(self, serializer):
        uploaded = serializer.validated_data["file"]
        content_type = check_upload(uploaded)
        user = self.request.user
        instance = serializer.save(
            organization_id=user.organization_id, branch=self.request.branch, created_by=user, updated_by=user,
            original_name=uploaded.name[:255], content_type=content_type, size_bytes=uploaded.size,
        )
        log_action(self.request, "create", instance, changes={"file": instance.original_name})

    @action(detail=True, methods=["get"])
    def file(self, request, pk=None):
        """Open (?download=0) or download (?download=1) the file. Both are written to the audit log."""
        document = self.get_object()
        download = request.query_params.get("download") == "1"
        log_action(request, "export" if download else "view", document)
        return FileResponse(
            document.file.open("rb"), content_type=document.content_type,
            as_attachment=download, filename=document.original_name,
        )


class ConsentPurposeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConsentPurposeSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    pagination_class = None

    def get_queryset(self):
        return ConsentPurpose.objects.filter(organization_id=self.request.user.organization_id, is_active=True)


class ConsentViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Consent history of one patient (?patient=<id>). Records are only ever added:
    to withdraw, add a new record with granted=false.
    """

    serializer_class = ConsentSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_required = True
    pagination_class = None
    required_permissions = {
        "list": "patients.view",
        "status": "patients.view",
        "create": ("patients.create", "patients.edit"),
    }

    def get_queryset(self):
        return PatientConsent.objects.filter(
            organization_id=self.request.user.organization_id, patient=required_patient_param(self.request),
        ).select_related("purpose", "branch", "created_by")

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "branch": self.request.branch}

    def perform_create(self, serializer):
        user = self.request.user
        purpose = serializer.validated_data["purpose"]
        instance = serializer.save(
            organization_id=user.organization_id, branch=self.request.branch,
            purpose_version=purpose.version, created_by=user, updated_by=user,
        )
        log_action(self.request, "create", instance, changes={
            "purpose": purpose.code, "granted": instance.granted, "method": instance.method,
        })

    @action(detail=False, methods=["get"])
    def status(self, request):
        """Current consent per purpose for one patient."""
        patient = required_patient_param(request)
        latest = current_consents(patient)
        rows = []
        for purpose in ConsentPurpose.objects.filter(organization_id=request.user.organization_id, is_active=True):
            record = latest.get(purpose.code)
            rows.append({
                "purpose": ConsentPurposeSerializer(purpose).data,
                "granted": record.granted if record else None,
                "since": record.created_at if record else None,
                "outdated": bool(record and record.granted and record.purpose_version < purpose.version),
            })
        return Response(rows)
