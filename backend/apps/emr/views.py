from datetime import date as date_cls

from django.utils import timezone
from rest_framework import status as http
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.appointments.models import Appointment
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.patients.models import Patient

from .models import ExamTemplate, Visit
from .serializers import (
    ExamTemplateSerializer, StartVisitSerializer, VisitExamSerializer, VisitListSerializer, VisitSerializer,
)
from .services import complete_visit, save_exam, start_visit

MEDICAL_FIELDS = {
    "complaints", "history_notes", "examination_notes", "diagnoses", "advice", "advice_notes", "follow_up_notes",
}


class ExamTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """The Ayurveda check-up templates of the clinic (Ashtavidha, Prakriti...)."""

    serializer_class = ExamTemplateSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_required = True
    required_permissions = {"list": "emr.view", "retrieve": "emr.view"}
    pagination_class = None

    def get_queryset(self):
        return ExamTemplate.objects.filter(organization_id=self.request.user.organization_id, is_active=True)


class VisitViewSet(AuditedModelViewSet):
    """
    Check-ups. A patient's visits from ALL branches are shown (?patient=<id>), because the doctor needs
    the full history. Without ?patient: the visits of the current branch on one day (?date=, default today).
    Opening a visit is written to the audit log; the medical text itself is never copied into the log.
    """

    queryset = Visit.objects.select_related("patient", "doctor", "branch", "appointment").prefetch_related("exams")
    serializer_class = VisitSerializer
    branch_required = True
    http_method_names = ["get", "post", "patch", "put", "head", "options"]
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
    }

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
