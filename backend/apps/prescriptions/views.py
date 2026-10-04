from datetime import date as date_cls

from django.utils import timezone
from rest_framework import mixins, status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.emr.models import Visit
from apps.patients.models import Patient

from .models import Prescription, PrescriptionTemplate
from .safety import check_prescription
from .serializers import PrescriptionSerializer, PrescriptionTemplateSerializer, clean_lines
from .services import lines_for_check, save_prescription


class PrescriptionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    Prescriptions.  ?visit=<id>  the prescription of one check-up   ?patient=<id>  all of a patient (all branches)
    ?date=YYYY-MM-DD (default today) + ?status=final   this branch's prescriptions of a day (pharmacy)
    Writing (POST / PATCH) needs prescriptions.create. Every view and change is in the audit log.
    """

    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated, BranchPermission]
    branch_required = True
    required_permissions = {
        "list": "prescriptions.view", "retrieve": "prescriptions.view",
        "create": "prescriptions.create", "partial_update": "prescriptions.create", "check": "prescriptions.create",
    }

    def get_queryset(self):
        qs = Prescription.objects.filter(organization_id=self.request.user.organization_id).select_related(
            "patient", "doctor", "branch", "visit",
        )
        if self.action != "list":
            return qs
        params = self.request.query_params
        if params.get("visit"):
            return qs.filter(visit_id=params["visit"])
        if params.get("patient"):
            return qs.filter(patient_id=params["patient"])
        try:
            day = date_cls.fromisoformat(params["date"]) if params.get("date") else timezone.localdate()
        except ValueError:
            raise ValidationError({"date": "Date must look like 2026-10-05."})
        qs = qs.filter(branch=self.request.branch, visit__visit_date=day)
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        return qs

    def retrieve(self, request, *args, **kwargs):
        prescription = self.get_object()
        log_action(request, "view", prescription, changes={"patient": str(prescription.patient_id)})
        return Response(self.get_serializer(prescription).data)

    def create(self, request, *args, **kwargs):
        visit = Visit.objects.filter(organization_id=request.user.organization_id, pk=request.data.get("visit")).first()
        if visit is None:
            raise NotFound("Check-up not found.")
        if hasattr(visit, "prescription"):
            raise ValidationError({"visit": "This check-up already has a prescription. Edit it instead."})
        lines = clean_lines(self.get_serializer_context(), request.data.get("items", []))
        prescription = save_prescription(visit, lines, request.data.get("notes", ""), request.user)
        log_action(request, "create", prescription, changes={"patient": str(visit.patient_id), "lines": len(lines)})
        return Response(self.get_serializer(prescription).data, status=http.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        prescription = self.get_object()
        if "items" in request.data:
            lines = clean_lines(self.get_serializer_context(), request.data["items"])
        else:
            lines = [{"id": i.id, "medicine": i.medicine, "medicine_name": i.medicine_name}
                     for i in prescription.items.select_related("medicine")]
        notes = request.data.get("notes") if "notes" in request.data else None
        save_prescription(prescription.visit, lines, notes, request.user, prescription=prescription)
        log_action(request, "update", prescription, changes={
            "patient": str(prescription.patient_id), "lines": len(lines), **({"notes": "changed"} if notes is not None else {}),
        })
        prescription.refresh_from_db()
        return Response(self.get_serializer(prescription).data)

    @action(detail=False, methods=["post"])
    def check(self, request):
        """Safety warnings for lines not saved yet: {patient, items}."""
        patient = Patient.objects.filter(organization_id=request.user.organization_id, pk=request.data.get("patient")).first()
        if patient is None:
            raise NotFound("Patient not found.")
        lines = clean_lines(self.get_serializer_context(), request.data.get("items", []))
        return Response({"warnings": check_prescription(patient, lines_for_check(lines))})


class PrescriptionTemplateViewSet(AuditedModelViewSet):
    """Disease-wise prescription templates. Never deleted: switch them off (is_active)."""

    queryset = PrescriptionTemplate.objects.select_related("diagnosis")
    serializer_class = PrescriptionTemplateSerializer
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None
    required_permissions = {
        "list": "prescriptions.view", "retrieve": "prescriptions.view",
        "create": "prescriptions.create", "partial_update": "prescriptions.create",
    }

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("all") != "1":
            qs = qs.filter(is_active=True)
        return qs.order_by("name")
