"""OPD billing API: services & charges list, doctors' consultation fees, and charging an OPD bill."""
from rest_framework import status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.accounts.services import doctors_in_branch, user_has_perm
from apps.appointments.models import Appointment
from apps.appointments.serializers import patient_summary
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.emr.models import Visit
from apps.patients.models import Patient

from .models import BranchServicePrice, ConsultationFee, ServiceCharge
from .opd import branch_services, charge_opd, clean_desk_lines, opd_bill_for, suggest_consultation
from .serializers import BranchPriceInput, ChargeInput, ConsultationFeeInput, InvoiceSerializer, ServiceChargeSerializer


class ServiceChargeViewSet(AuditedModelViewSet):
    """
    The "Services & charges" list (organization-wide) with this branch's price.
    ?active=1 only services in use in this branch (for the bill screen).
    """

    queryset = ServiceCharge.objects.select_related("category")
    serializer_class = ServiceChargeSerializer
    permission_prefix = "billing"  # billing.view to read, billing.manage to change
    branch_required = True
    pagination_class = None
    http_method_names = ["get", "post", "patch", "head", "options"]
    required_permissions = {
        "list": ("billing.view", "billing.charge"), "retrieve": ("billing.view", "billing.charge"),
        "branch_price": "billing.manage",
    }

    def list(self, request, *args, **kwargs):
        rows = branch_services(request.branch, active_only=request.query_params.get("active") == "1")
        for row in rows:
            row["service"].branch_price = row["branch_price"]
            row["service"].branch_active = row["active"]
            row["service"].effective_price = row["price"]
        return Response(self.get_serializer([r["service"] for r in rows], many=True).data)

    @action(detail=True, methods=["post"], url_path="branch-price")
    def branch_price(self, request, pk=None):
        """This branch's own price (empty = organization price) and on/off."""
        service = self.get_object()
        data = BranchPriceInput(data=request.data)
        data.is_valid(raise_exception=True)
        row, _ = BranchServicePrice.objects.update_or_create(
            organization_id=service.organization_id, branch=request.branch, service=service,
            defaults={"price": data.validated_data.get("price"), "is_active": data.validated_data["is_active"],
                      "updated_by": request.user, "created_by": request.user},
        )
        log_action(request, "update", service, changes={"branch_price": str(row.price), "branch_active": row.is_active})
        return Response({"id": str(service.id), "branch_price": str(row.price) if row.price is not None else None,
                         "branch_active": row.is_active})


class ConsultationFeeViewSet(viewsets.ViewSet):
    """Consultation fee of every doctor of this branch (new case / follow-up, follow-up days)."""

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True
    required_permissions = {"list": ("billing.view", "billing.charge"), "set_fee": "billing.manage"}

    def list(self, request):
        fees = {f.doctor_id: f for f in ConsultationFee.objects.filter(branch=request.branch)}
        rows = []
        for doctor in doctors_in_branch(request.branch).order_by("full_name"):
            fee = fees.get(doctor.id)
            rows.append({
                "doctor": str(doctor.id), "doctor_name": doctor.full_name,
                "new_case_fee": str(fee.new_case_fee) if fee else None,
                "follow_up_fee": str(fee.follow_up_fee) if fee else None,
                "follow_up_days": fee.follow_up_days if fee else 15, "is_set": fee is not None,
            })
        return Response(rows)

    @action(detail=False, methods=["post"], url_path="set")
    def set_fee(self, request):
        data = ConsultationFeeInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        doctor = doctors_in_branch(request.branch).filter(pk=v["doctor"]).first()
        if doctor is None:
            raise ValidationError({"doctor": "This doctor does not work in this branch."})
        fee, _ = ConsultationFee.objects.update_or_create(
            organization_id=request.branch.organization_id, branch=request.branch, doctor=doctor,
            defaults={"new_case_fee": v["new_case_fee"], "follow_up_fee": v["follow_up_fee"],
                      "follow_up_days": v["follow_up_days"], "updated_by": request.user, "created_by": request.user},
        )
        log_action(request, "update", fee, changes={k: str(v[k]) for k in ("new_case_fee", "follow_up_fee", "follow_up_days")})
        return Response({"doctor": str(doctor.id), "new_case_fee": str(fee.new_case_fee),
                         "follow_up_fee": str(fee.follow_up_fee), "follow_up_days": fee.follow_up_days, "is_set": True})


class OpdBillViewSet(viewsets.ViewSet):
    """
    The OPD bill of a visit / appointment.
    GET  /opd-bills/suggest/?appointment= | ?visit= | ?patient=&doctor=  -> patient, doctor, suggested
         consultation (new case / follow-up, fee) and the bill made so far.
    POST /opd-bills/charge/  -> make the bill or add lines; optional payment now.
    """

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True
    required_permissions = {"suggest": ("billing.charge", "billing.create"), "charge": ("billing.charge", "billing.create")}

    def _context(self, request, *, appointment=None, visit=None, patient=None, doctor=None):
        branch = request.branch
        org = request.user.organization_id
        if appointment:
            appointment = Appointment.objects.filter(branch=branch, pk=appointment).select_related("patient", "doctor").first()
            if appointment is None:
                raise NotFound("Appointment not found.")
            if appointment.status == "cancelled":
                raise ValidationError({"detail": "This appointment is cancelled."})
            visit = getattr(appointment, "visit", None)
            return appointment, visit, appointment.patient, appointment.doctor
        if visit:
            visit = Visit.objects.filter(branch=branch, pk=visit).select_related("patient", "doctor", "appointment").first()
            if visit is None:
                raise NotFound("Check-up not found.")
            return visit.appointment, visit, visit.patient, visit.doctor
        if not patient:
            raise ValidationError({"detail": "Choose the patient."})
        patient = Patient.objects.filter(organization_id=org, pk=patient).first()
        if patient is None:
            raise NotFound("Patient not found.")
        doctor = doctors_in_branch(branch).filter(pk=doctor).first() if doctor else None
        return None, None, patient, doctor

    @action(detail=False, methods=["get"])
    def suggest(self, request):
        p = request.query_params
        appointment, visit, patient, doctor = self._context(
            request, appointment=p.get("appointment"), visit=p.get("visit"), patient=p.get("patient"), doctor=p.get("doctor"))
        bill = opd_bill_for(appointment=appointment, visit=visit) if (appointment or visit) else None
        consultation = suggest_consultation(request.branch, patient, doctor) if doctor else None
        has_consultation = bool(bill and bill.lines.filter(kind="consultation").exists())
        return Response({
            "appointment": str(appointment.id) if appointment else None, "visit": str(visit.id) if visit else None,
            "patient_detail": patient_summary(patient),
            "doctor": str(doctor.id) if doctor else None, "doctor_name": doctor.full_name if doctor else "",
            "consultation": {**consultation, "fee": str(consultation["fee"]),
                             "last_visit": consultation["last_visit"]} if consultation else None,
            "consultation_billed": has_consultation,
            "bill": InvoiceSerializer(bill).data if bill else None,
        })

    @action(detail=False, methods=["post"])
    def charge(self, request):
        data = ChargeInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        payment = v.get("payment")
        if payment and payment["amount"] > 0 and not user_has_perm(request.user, "billing.create", request.branch):
            raise PermissionDenied("Only staff who take payments can record a payment.")
        appointment, visit, patient, doctor = self._context(
            request, appointment=v.get("appointment"), visit=v.get("visit"), patient=v.get("patient"), doctor=v.get("doctor"))
        lines = clean_desk_lines(request.user.organization_id, [dict(line) for line in v["lines"]])
        invoice = charge_opd(request.branch, request.user, patient=patient, doctor=doctor, lines=lines,
                             appointment=appointment, visit=visit, payment=payment)
        log_action(request, "create", invoice, changes={
            "patient": str(patient.id), "lines": len(lines), "total": str(invoice.total_amount),
            "payment": str(payment["amount"]) if payment else "0"})
        return Response(InvoiceSerializer(invoice).data, status=http.HTTP_201_CREATED)
