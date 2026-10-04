from datetime import date as date_cls

from django.http import FileResponse
from django.utils import timezone
from rest_framework import status as http
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.appointments.models import Appointment
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.patients.models import Patient
from apps.patients.services import IMAGE_TYPES, check_upload

from .models import PHOTO_KINDS, ExamTemplate, Visit, VisitPhoto
from .serializers import (
    ExamTemplateSerializer, StartVisitSerializer, VisitExamSerializer, VisitListSerializer, VisitPhotoSerializer,
    VisitSerializer,
)
from .services import complete_visit, create_template, save_exam, save_template, start_visit

MEDICAL_FIELDS = {
    "complaints", "history_notes", "examination_notes", "diagnoses", "advice", "advice_notes", "follow_up_notes",
}


class ExamTemplateViewSet(viewsets.ModelViewSet):
    """
    The Ayurveda check-up templates of the clinic (Ashtavidha, Prakriti...).
    Doctors read them; admins (settings.manage) add and edit them on the Templates screen.
    Changing the questions raises the version; old check-ups keep the old questions.
    Templates are never deleted - switch them off instead.
    """

    serializer_class = ExamTemplateSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    required_permissions = {
        "list": "emr.view", "retrieve": "emr.view",
        "create": "settings.manage", "partial_update": "settings.manage",
    }
    pagination_class = None

    def get_queryset(self):
        qs = ExamTemplate.objects.filter(organization_id=self.request.user.organization_id)
        if self.request.query_params.get("all") != "1":
            qs = qs.filter(is_active=True)
        return qs

    def create(self, request, *args, **kwargs):
        template = create_template(request.user.organization, request.data, request.user)
        log_action(request, "create", template, changes={"name": template.name})
        return Response(self.get_serializer(template).data, status=http.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        template = self.get_object()
        old_version = template.version
        template = save_template(template, request.data, request.user)
        changes = {"version": {"from": old_version, "to": template.version}} if template.version != old_version else {}
        log_action(request, "update", template, changes={**changes, "name": template.name})
        return Response(self.get_serializer(template).data)


class VisitViewSet(AuditedModelViewSet):
    """
    Check-ups. A patient's visits from ALL branches are shown (?patient=<id>), because the doctor needs
    the full history. Without ?patient: the visits of the current branch on one day (?date=, default today).
    Opening a visit is written to the audit log; the medical text itself is never copied into the log.
    """

    queryset = Visit.objects.select_related("patient", "doctor", "branch", "appointment").prefetch_related(
        "exams__template", "photos")
    serializer_class = VisitSerializer
    branch_required = True
    http_method_names = ["get", "post", "patch", "put", "delete", "head", "options"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    audit_redact_fields = MEDICAL_FIELDS
    filterset_fields = ["doctor", "status"]
    required_permissions = {
        "list": "emr.view",
        "retrieve": "emr.view",
        "create": "emr.edit",
        "update": "emr.edit",
        "partial_update": "emr.edit",
        "complete": "emr.edit",
        "save_exam": "emr.edit",
        "upload_photo": "emr.edit",
        "photo_file": "emr.view",
        "delete_photo": "emr.edit",
        "patient_photos": "emr.view",
    }

    def destroy(self, request, *args, **kwargs):
        raise ValidationError({"detail": "Check-ups are never deleted."})

    def get_serializer_class(self):
        return VisitListSerializer if self.action == "list" else VisitSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action != "list":
            return qs
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            return qs.filter(patient_id=patient_id).order_by("-visit_date", "-created_at")
        raw = self.request.query_params.get("date")
        try:
            day = date_cls.fromisoformat(raw) if raw else timezone.localdate()
        except ValueError:
            raise ValidationError({"date": "Date must look like 2026-10-05."})
        return qs.filter(branch=self.request.branch, visit_date=day)

    def retrieve(self, request, *args, **kwargs):
        visit = self.get_object()
        log_action(request, "view", visit, changes={"patient": str(visit.patient_id)})
        return Response(self.get_serializer(visit).data)

    def create(self, request, *args, **kwargs):
        """Open a check-up: from an appointment (preferred) or for a patient directly (doctors only)."""
        data = StartVisitSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        org_id = request.user.organization_id
        appointment = None
        if data.validated_data.get("appointment"):
            appointment = (
                Appointment.objects.select_related("patient", "doctor")
                .filter(organization_id=org_id, branch=request.branch, pk=data.validated_data["appointment"]).first()
            )
            if appointment is None:
                raise NotFound("Appointment not found in this branch.")
            if appointment.status in ("cancelled", "no_show"):
                raise ValidationError({"detail": "This appointment was cancelled or the patient did not come."})
            patient, doctor = appointment.patient, appointment.doctor
        else:
            patient = Patient.objects.filter(organization_id=org_id, pk=data.validated_data["patient"]).first()
            if patient is None:
                raise NotFound("Patient not found.")
            if not request.user.is_doctor:
                raise ValidationError({"detail": "Only a doctor can start a check-up without an appointment."})
            doctor = request.user
        visit, created = start_visit(
            patient=patient, doctor=doctor, branch=request.branch, user=request.user, appointment=appointment,
        )
        if created:
            log_action(request, "create", visit, changes={"patient": str(patient.id)})
        return Response(VisitSerializer(visit, context=self.get_serializer_context()).data,
                        status=http.HTTP_201_CREATED if created else http.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        visit = complete_visit(self.get_object(), request.user)
        log_action(request, "update", visit, changes={"status": {"from": "draft", "to": "completed"}})
        return Response(VisitSerializer(visit, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["put"], url_path=r"exams/(?P<code>[a-z0-9_-]+)")
    def save_exam(self, request, pk=None, code=None):
        """Save the answers of one template (e.g. PUT /visits/<id>/exams/prakriti/ {"values": {...}})."""
        visit = self.get_object()
        template = ExamTemplate.objects.filter(organization_id=visit.organization_id, code=code).first()
        if template is None:
            raise NotFound("Template not found.")
        exam = save_exam(visit, template, request.data.get("values", {}), request.user)
        log_action(request, "update", visit, changes={"exam": code, "patient": str(visit.patient_id)})
        return Response(VisitExamSerializer(exam).data)

    # --- Before / after photos ---------------------------------------------------------------
    @action(detail=True, methods=["post"], url_path="photos")
    def upload_photo(self, request, pk=None):
        visit = self.get_object()
        uploaded = request.FILES.get("file")
        if not uploaded:
            raise ValidationError({"file": "Choose a photo."})
        content_type = check_upload(uploaded, IMAGE_TYPES)
        kind = request.data.get("kind") or "before"
        if kind not in dict(PHOTO_KINDS):
            raise ValidationError({"kind": "Choose before, during or after."})
        photo = VisitPhoto(
            organization_id=visit.organization_id, visit=visit, kind=kind,
            caption=str(request.data.get("caption") or "")[:200], content_type=content_type,
            size_bytes=uploaded.size, created_by=request.user, updated_by=request.user,
        )
        photo.file.save(uploaded.name, uploaded, save=False)
        photo.save()
        log_action(request, "create", photo, changes={"kind": kind, "caption": photo.caption})
        return Response(VisitPhotoSerializer(photo).data, status=http.HTTP_201_CREATED)

    def _photo(self, pk, photo_id):
        visit = self.get_object()
        photo = VisitPhoto.objects.filter(visit=visit, pk=photo_id).first()
        if photo is None:
            raise NotFound("Photo not found.")
        return photo

    @action(detail=True, methods=["get"], url_path=r"photos/(?P<photo_id>[0-9a-f-]{36})/file")
    def photo_file(self, request, pk=None, photo_id=None):
        photo = self._photo(pk, photo_id)
        log_action(request, "view", photo)
        return FileResponse(photo.file.open("rb"), content_type=photo.content_type)

    @action(detail=True, methods=["delete"], url_path=r"photos/(?P<photo_id>[0-9a-f-]{36})")
    def delete_photo(self, request, pk=None, photo_id=None):
        photo = self._photo(pk, photo_id)
        photo.delete(user=request.user)  # soft delete: the file is kept
        log_action(request, "delete", photo)
        return Response(status=http.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="patient-photos")
    def patient_photos(self, request):
        """All photos of one patient (all visits, all branches), oldest first - for before/after comparison."""
        patient_id = request.query_params.get("patient")
        if not patient_id:
            raise ValidationError({"patient": "Choose a patient."})
        photos = VisitPhoto.objects.filter(
            organization_id=request.user.organization_id, visit__patient_id=patient_id,
        ).select_related("visit").order_by("visit__visit_date", "created_at")
        return Response(VisitPhotoSerializer(photos, many=True).data)
