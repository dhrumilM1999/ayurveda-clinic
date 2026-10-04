from datetime import date as date_cls

from django.utils import timezone
from rest_framework import mixins, status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.appointments.serializers import patient_summary
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.medicines.models import Medicine
from apps.organizations.services import is_feature_enabled
from apps.prescriptions.models import Prescription

from .models import Purchase, StockBatch, StockMovement, Supplier
from .serializers import (
    AdjustInput, BatchSerializer, DispenseInput, MovementSerializer, PurchaseInput, PurchaseSerializer, SupplierSerializer,
)
from .services import (
    adjust_stock, dispense, dispense_status, dispensed_quantities, receive_purchase, set_reorder_level, stock_summary,
    suggested_batches,
)


class PharmacyMixin:
    """All pharmacy screens: current branch, and the Pharmacy module must be switched on (Settings)."""

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True

    def check_permissions(self, request):
        super().check_permissions(request)
        branch = getattr(request, "branch", None)
        if branch is not None and not is_feature_enabled(branch, "pharmacy"):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Pharmacy is switched off for this branch (Settings -> Modules).")


def money(value):
    return str(value) if value is not None else None


class SupplierViewSet(PharmacyMixin, AuditedModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    branch_scoped = False
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None
    required_permissions = {
        "list": "pharmacy.view", "retrieve": "pharmacy.view", "create": "pharmacy.stock", "partial_update": "pharmacy.stock",
    }


class PurchaseViewSet(PharmacyMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Stock received from suppliers (this branch)."""

    serializer_class = PurchaseSerializer
    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view", "create": "pharmacy.stock"}

    def get_queryset(self):
        return (Purchase.objects.filter(branch=self.request.branch)
                .select_related("supplier", "created_by").prefetch_related("items__medicine", "items__batch"))

    def create(self, request):
        data = PurchaseInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        org_id = request.user.organization_id
        supplier = None
        if v.get("supplier"):
            supplier = Supplier.objects.filter(organization_id=org_id, pk=v["supplier"]).first()
            if supplier is None:
                raise ValidationError({"supplier": "Supplier not found."})
        medicines = {m.id: m for m in Medicine.objects.filter(organization_id=org_id, id__in=[i["medicine"] for i in v["items"]])}
        items = []
        for line in v["items"]:
            medicine = medicines.get(line["medicine"])
            if medicine is None:
                raise ValidationError({"items": "A medicine was not found."})
            items.append({**line, "medicine": medicine})
        purchase = receive_purchase(request.branch, request.user, supplier=supplier, invoice_no=v.get("invoice_no", ""),
                                    invoice_date=v["invoice_date"], notes=v.get("notes", ""), items=items)
        log_action(request, "create", purchase, changes={"lines": len(items), "total": str(purchase.total_amount)})
        return Response(self.get_serializer(self.get_queryset().get(pk=purchase.pk)).data, status=http.HTTP_201_CREATED)


class StockViewSet(PharmacyMixin, viewsets.ViewSet):
    """Stock of this branch: summary per medicine, batches, corrections, low-stock levels, history."""

    required_permissions = {
        "list": "pharmacy.view", "batches": "pharmacy.view", "movements": "pharmacy.view",
        "adjust": "pharmacy.stock", "reorder_level": "pharmacy.stock",
    }

    def list(self, request):
        show = request.query_params.get("show", "all")
        rows = stock_summary(request.branch, request.query_params.get("q", "").strip(), show)
        return Response([{
            "medicine": str(r["medicine"].id), "name": r["medicine"].name, "kind": r["medicine"].kind,
            "pack_size": r["medicine"].pack_size, "available": money(r["available"]), "usable": money(r["usable"]),
            "nearest_expiry": r["nearest_expiry"], "reorder_level": money(r["reorder_level"]),
            "low": r["low"], "expiring": r["expiring"], "expired": r["expired"],
        } for r in rows])

    @action(detail=False, methods=["get"])
    def batches(self, request):
        medicine_id = request.query_params.get("medicine")
        qs = StockBatch.objects.filter(branch=request.branch).select_related("medicine")
        if medicine_id:
            qs = qs.filter(medicine_id=medicine_id)
        if request.query_params.get("in_stock") == "1":
            qs = qs.filter(quantity__gt=0)
        return Response(BatchSerializer(qs.order_by("expiry_date", "created_at"), many=True).data)

    @action(detail=False, methods=["get"])
    def movements(self, request):
        qs = StockMovement.objects.filter(branch=request.branch).select_related("batch", "created_by")
        if request.query_params.get("medicine"):
            qs = qs.filter(medicine_id=request.query_params["medicine"])
        return Response(MovementSerializer(qs[:200], many=True).data)

    @action(detail=False, methods=["post"])
    def adjust(self, request):
        data = AdjustInput(data=request.data)
        data.is_valid(raise_exception=True)
        batch = adjust_stock(data.validated_data["batch"], request.branch, data.validated_data["change"],
                             data.validated_data["reason"], request.user)
        log_action(request, "update", batch, changes={"change": str(data.validated_data["change"]),
                                                       "reason": data.validated_data["reason"]})
        return Response(BatchSerializer(batch).data)

    @action(detail=False, methods=["post"], url_path="reorder-level")
    def reorder_level(self, request):
        medicine = Medicine.objects.filter(organization_id=request.user.organization_id, pk=request.data.get("medicine")).first()
        if medicine is None:
            raise NotFound("Medicine not found.")
        raw = request.data.get("level")
        try:
            level = None if raw in (None, "") else max(0, float(raw))
        except (TypeError, ValueError):
            raise ValidationError({"level": "Enter a number."})
        set_reorder_level(medicine, request.branch, level, request.user)
        return Response({"medicine": str(medicine.id), "reorder_level": level})


class DispensingViewSet(PharmacyMixin, viewsets.ViewSet):
    """Prescriptions to dispense (final prescriptions of this branch) and dispensing them."""

    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view", "dispense": "pharmacy.dispense"}

    def _prescriptions(self, request):
        return (Prescription.objects.filter(branch=request.branch, status="final")
                .select_related("patient", "doctor", "visit__appointment").prefetch_related("items"))

    def list(self, request):
        raw = request.query_params.get("date")
        try:
            day = date_cls.fromisoformat(raw) if raw else timezone.localdate()
        except ValueError:
            raise ValidationError({"date": "Date must look like 2026-10-05."})
        wanted = request.query_params.get("status")  # pending | partly | done
        rows = []
        for rx in self._prescriptions(request).filter(visit__visit_date=day).order_by("finalized_at"):
            status = dispense_status(rx)
            if wanted and status != wanted:
                continue
            appointment = getattr(rx.visit, "appointment", None)
            rows.append({
                "id": str(rx.id), "patient_detail": patient_summary(rx.patient), "doctor_name": rx.doctor.full_name,
                "token_number": appointment.token_number if appointment else None,
                "finalized_at": rx.finalized_at, "item_count": len(rx.items.all()), "status": status,
            })
        return Response(rows)

    def retrieve(self, request, pk=None):
        rx = self._prescriptions(request).filter(pk=pk).first()
        if rx is None:
            raise NotFound("Prescription not found (or not final yet).")
        log_action(request, "view", rx, changes={"patient": str(rx.patient_id), "screen": "pharmacy"})
        items = list(rx.items.select_related("medicine"))
        given = dispensed_quantities(rx)
        batches = suggested_batches(request.branch, [i.medicine_id for i in items if i.medicine_id])
        return Response({
            "id": str(rx.id), "patient_detail": patient_summary(rx.patient), "doctor_name": rx.doctor.full_name,
            "notes": rx.notes, "status": dispense_status(rx),
            "lines": [{
                "id": str(i.id), "medicine": str(i.medicine_id) if i.medicine_id else None,
                "medicine_name": i.medicine_name, "dosage_form": i.dosage_form, "pack_size": i.medicine.pack_size if i.medicine else "",
                "dose": i.dose, "dose_unit": i.dose_unit, "frequency": i.frequency, "timing": i.timing, "anupana": i.anupana,
                "duration": i.duration, "duration_unit": i.duration_unit, "instructions": i.instructions,
                "given": money(given.get(i.id)),
                "batches": BatchSerializer(batches.get(i.medicine_id, []), many=True).data,
            } for i in items],
        })

    @action(detail=True, methods=["post"])
    def dispense(self, request, pk=None):
        rx = self._prescriptions(request).filter(pk=pk).first()
        if rx is None:
            raise NotFound("Prescription not found (or not final yet).")
        data = DispenseInput(data=request.data)
        data.is_valid(raise_exception=True)
        items = {i.id: i for i in rx.items.all()}
        lines = []
        for line in data.validated_data["items"]:
            item = items.get(line["prescription_item"])
            if item is None:
                raise ValidationError({"items": "A line does not belong to this prescription."})
            lines.append({"prescription_item": item, "batch_id": line["batch"], "quantity": line["quantity"]})
        record = dispense(rx, request.branch, request.user, lines, data.validated_data.get("notes", ""))
        log_action(request, "create", record, changes={"patient": str(rx.patient_id), "lines": len(lines),
                                                        "total": str(record.total_amount)})
        return Response({"id": str(record.id), "total_amount": str(record.total_amount), "status": dispense_status(rx)},
                        status=http.HTTP_201_CREATED)
