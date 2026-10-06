from datetime import date as date_cls

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import mixins, status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import BranchPermission
from apps.appointments.serializers import patient_summary
from apps.audit.services import log_action
from apps.common.viewsets import AuditedModelViewSet
from apps.medicines.models import Medicine
from apps.organizations.services import is_feature_enabled
from apps.prescriptions.models import Prescription

from .models import Dispense, Purchase, PurchaseReturn, Rack, StockBatch, StockVerification, StockVerificationItem, Supplier
from .serializers import (
    AdjustInput, BatchSerializer, CountInput, LocationInput, MovementSerializer, PurchaseInput, PurchaseReturnInput,
    PurchaseReturnSerializer, PurchaseSerializer, RackSerializer, SaleReturnInput, SellInput, SupplierSerializer,
    VerificationItemSerializer, VerificationSerializer,
)
from .services import (
    alert_counts, complete_verification, correct_stock, dispense_status, dispensed_quantities, ledger, locations_for,
    receive_stock, return_to_supplier, scan, sell, set_location, set_reorder_level, start_verification, stock_summary,
    suggested_batches, take_back,
)


def _day(raw, default=None):
    if not raw:
        return default
    try:
        return date_cls.fromisoformat(raw)
    except ValueError:
        raise ValidationError({"date": "Date must look like 2026-10-05."})


def money(value):
    return str(value) if value is not None else None


class PharmacyMixin:
    """
    All pharmacy screens: current branch, and the Pharmacy module must be switched on (Settings).
    required_features: {action: additional feature code} ("*" = every action). Those extras must be
    switched on by the organization admin in Additional settings.
    """

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True
    required_features: dict[str, str] = {}

    def check_permissions(self, request):
        super().check_permissions(request)
        branch = getattr(request, "branch", None)
        if branch is None:
            return
        if not is_feature_enabled(branch, "pharmacy"):
            raise PermissionDenied("Pharmacy is switched off for this branch (Settings -> Modules).")
        code = self.required_features.get(getattr(self, "action", None)) or self.required_features.get("*")
        if code:
            self.need_feature(request, code)

    def need_feature(self, request, code):
        if not is_feature_enabled(request.branch, code):
            raise PermissionDenied(f"This feature is switched off ({code}). An admin can switch it on in Additional settings.")

    def _medicine(self, request, medicine_id):
        medicine = Medicine.objects.filter(organization_id=request.user.organization_id, pk=medicine_id).first()
        if medicine is None:
            raise NotFound("Medicine not found.")
        return medicine


# --- Racks and suppliers ------------------------------------------------------------------------
class RackViewSet(PharmacyMixin, AuditedModelViewSet):
    queryset = Rack.objects.all()
    required_features = {"*": "pharmacy_racks"}
    serializer_class = RackSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None
    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view",
                            "create": "pharmacy.stock", "partial_update": "pharmacy.stock"}

    def get_queryset(self):
        return super().get_queryset().annotate(
            product_count=Count("products", filter=Q(products__is_deleted=False), distinct=True))


class SupplierViewSet(PharmacyMixin, AuditedModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    branch_scoped = False
    branch_required = True
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None
    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view",
                            "create": "pharmacy.stock", "partial_update": "pharmacy.stock"}


# --- Purchases, opening stock, purchase returns ----------------------------------------------------
class PurchaseViewSet(PharmacyMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Stock received: supplier invoices, and opening stock (?opening=1)."""

    serializer_class = PurchaseSerializer
    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view", "create": "pharmacy.stock"}

    def get_queryset(self):
        qs = purchases_of(self.request.branch)
        p = self.request.query_params
        if p.get("opening") in ("0", "1"):
            qs = qs.filter(is_opening=p["opening"] == "1")
        if p.get("supplier"):
            qs = qs.filter(supplier_id=p["supplier"])
        if p.get("date_from"):
            qs = qs.filter(invoice_date__gte=_day(p["date_from"]))
        if p.get("date_to"):
            qs = qs.filter(invoice_date__lte=_day(p["date_to"]))
        if p.get("q", "").strip():
            q = p["q"].strip()
            qs = qs.filter(Q(invoice_no__icontains=q) | Q(supplier__name__icontains=q)
                           | Q(items__medicine__name__icontains=q) | Q(items__batch__batch_no__iexact=q)).distinct()
        return qs

    def create(self, request):
        data = PurchaseInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        if v.get("is_opening"):
            self.need_feature(request, "pharmacy_opening_stock")
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
            items.append({**line, "medicine": medicine, "gst_rate": line.get("gst_rate", medicine.gst_rate)})
        purchase = receive_stock(request.branch, request.user, items=items, supplier=supplier,
                                 invoice_no=v.get("invoice_no", ""), invoice_date=v.get("invoice_date"),
                                 notes=v.get("notes", ""), other_charges=v.get("other_charges", 0),
                                 is_opening=v.get("is_opening", False))
        log_action(request, "create", purchase, changes={"lines": len(items), "total": str(purchase.total_amount),
                                                          "opening": purchase.is_opening})
        return Response(self.get_serializer(self.get_queryset().get(pk=purchase.pk)).data, status=http.HTTP_201_CREATED)


def purchases_of(branch):
    return (Purchase.objects.filter(branch=branch)
            .select_related("supplier", "created_by").prefetch_related("items__medicine", "items__batch"))


class PurchaseReturnViewSet(PharmacyMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = PurchaseReturnSerializer
    required_features = {"*": "pharmacy_supplier_returns"}
    required_permissions = {"list": "pharmacy.view", "create": "pharmacy.stock"}

    def get_queryset(self):
        return (PurchaseReturn.objects.filter(branch=self.request.branch)
                .select_related("supplier", "created_by").prefetch_related("items__medicine", "items__batch"))

    def create(self, request):
        data = PurchaseReturnInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        supplier = None
        if v.get("supplier"):
            supplier = Supplier.objects.filter(organization_id=request.user.organization_id, pk=v["supplier"]).first()
        record = return_to_supplier(request.branch, request.user, supplier=supplier, reason=v["reason"],
                                    reference=v.get("reference", ""),
                                    items=[{"batch_id": i["batch"], "quantity": i["quantity"]} for i in v["items"]])
        log_action(request, "create", record, changes={"lines": len(v["items"]), "total": str(record.total_amount)})
        return Response(self.get_serializer(self.get_queryset().get(pk=record.pk)).data, status=http.HTTP_201_CREATED)


# --- Stock ---------------------------------------------------------------------------------------
class StockViewSet(PharmacyMixin, viewsets.ViewSet):
    """Stock of this branch: summary, alerts, batches, barcode scan, corrections, locations, ledger."""

    required_permissions = {
        "list": "pharmacy.view", "alerts": "pharmacy.view", "batches": "pharmacy.view", "scan": "pharmacy.view",
        "movements": "pharmacy.view", "adjust": "pharmacy.stock", "reorder_level": "pharmacy.stock",
        "location": "pharmacy.stock",
    }
    required_features = {"alerts": "pharmacy_stock_alerts", "scan": "pharmacy_barcode", "location": "pharmacy_racks"}

    def list(self, request):
        p = request.query_params
        rows = stock_summary(request.branch, p.get("q", "").strip(), p.get("show", "all"), p.get("rack"))
        return Response([{
            "medicine": str(r["medicine"].id), "name": r["medicine"].name, "kind": r["medicine"].kind,
            "generic_name": r["medicine"].generic_name, "manufacturer": r["medicine"].manufacturer,
            "category": r["medicine"].category.label if r["medicine"].category_id else "",
            "pack_size": r["medicine"].pack_size, "barcode": r["medicine"].barcode,
            "available": money(r["available"]), "usable": money(r["usable"]),
            "near_expiry_quantity": money(r["near_expiry_quantity"]), "nearest_expiry": r["nearest_expiry"],
            "reorder_level": money(r["reorder_level"]), "location": r["location"],
            "rack": str(r["rack_id"]) if r["rack_id"] else None, "shelf": r["shelf"], "bin": r["bin"],
            "low": r["low"], "out": r["out"], "expiring": r["expiring"], "expired": r["expired"],
        } for r in rows])

    @action(detail=False, methods=["get"])
    def alerts(self, request):
        return Response(alert_counts(request.branch))

    @action(detail=False, methods=["get"])
    def batches(self, request):
        qs = StockBatch.objects.filter(branch=request.branch).select_related("medicine", "supplier")
        if request.query_params.get("medicine"):
            qs = qs.filter(medicine_id=request.query_params["medicine"])
        if request.query_params.get("in_stock") == "1":
            qs = qs.filter(quantity__gt=0)
        return Response(BatchSerializer(qs.order_by("expiry_date", "created_at"), many=True).data)

    @action(detail=False, methods=["get"])
    def scan(self, request):
        """A barcode scanner types the code and presses Enter: ?code=..."""
        found = scan(request.branch, request.query_params.get("code", ""))
        m = found["medicine"]
        location = locations_for(request.branch, [m.id]).get(m.id)
        return Response({
            "medicine": str(m.id), "name": m.name, "pack_size": m.pack_size,
            "location": location.label if location else "",
            "scanned_batch": str(found["batch"].id) if found["batch"] else None,
            "batches": BatchSerializer(found["batches"], many=True).data,
        })

    @action(detail=False, methods=["get"])
    def movements(self, request):
        """Stock ledger: ?medicine= ?batch= ?kind= ?date_from= ?date_to=  (with opening / closing balance)."""
        p = request.query_params
        result = ledger(request.branch, medicine_id=p.get("medicine"), batch_id=p.get("batch"), kind=p.get("kind"),
                        date_from=_day(p.get("date_from")), date_to=_day(p.get("date_to")))
        return Response({
            "opening": str(result["opening"]), "closing": str(result["closing"]),
            "by_kind": {k: str(v) for k, v in result["by_kind"].items()},
            "lines": MovementSerializer(result["lines"], many=True).data,
        })

    @action(detail=False, methods=["post"])
    def adjust(self, request):
        data = AdjustInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        batch = correct_stock(v["batch"], request.branch, v["change"], v["reason"], request.user, kind=v["kind"])
        log_action(request, "update", batch, changes={"kind": v["kind"], "change": str(v["change"]), "reason": v["reason"]})
        return Response(BatchSerializer(batch).data)

    @action(detail=False, methods=["post"], url_path="reorder-level")
    def reorder_level(self, request):
        medicine = self._medicine(request, request.data.get("medicine"))
        raw = request.data.get("level")
        try:
            level = None if raw in (None, "") else max(0, float(raw))
        except (TypeError, ValueError):
            raise ValidationError({"level": "Enter a number."})
        set_reorder_level(medicine, request.branch, level, request.user)
        return Response({"medicine": str(medicine.id), "reorder_level": level})

    @action(detail=False, methods=["post"])
    def location(self, request):
        data = LocationInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        medicine = self._medicine(request, v["medicine"])
        rack = None
        if v.get("rack"):
            rack = Rack.objects.filter(branch=request.branch, pk=v["rack"]).first()
            if rack is None:
                raise ValidationError({"rack": "Rack not found."})
        row = set_location(medicine, request.branch, request.user, rack=rack, shelf=v.get("shelf", ""), bin_=v.get("bin", ""))
        return Response({"medicine": str(medicine.id), "location": row.label})


# --- Physical stock check ------------------------------------------------------------------------
class VerificationViewSet(PharmacyMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    required_features = {"*": "pharmacy_stock_check"}
    serializer_class = VerificationSerializer
    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view", "create": "pharmacy.stock",
                            "count": "pharmacy.stock", "complete": "pharmacy.stock"}

    def get_queryset(self):
        return (StockVerification.objects.filter(branch=self.request.branch)
                .select_related("rack", "created_by").prefetch_related("items"))

    def retrieve(self, request, pk=None):
        check = self.get_object()
        items = StockVerificationItem.objects.filter(verification=check).select_related("batch__medicine")
        locations = locations_for(request.branch)
        rows = VerificationItemSerializer(items, many=True).data
        for row, item in zip(rows, items):
            loc = locations.get(item.batch.medicine_id)
            row["location"] = loc.label if loc else ""
        return Response({**self.get_serializer(check).data, "items": rows})

    def create(self, request):
        rack = None
        if request.data.get("rack"):
            rack = Rack.objects.filter(branch=request.branch, pk=request.data["rack"]).first()
        title = str(request.data.get("title") or f"Stock check {timezone.localdate():%d-%m-%Y}")
        check = start_verification(request.branch, request.user, title=title, rack=rack, notes=str(request.data.get("notes", "")))
        log_action(request, "create", check, changes={"rack": rack.code if rack else "all"})
        return Response(self.get_serializer(self.get_queryset().get(pk=check.pk)).data, status=http.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def count(self, request, pk=None):
        """Save counted quantities: {"counts": [{"item", "counted_quantity"}]} (can be saved many times)."""
        check = self.get_object()
        if check.status != "open":
            raise ValidationError({"detail": "This stock check is already completed."})
        data = CountInput(data=request.data.get("counts", []), many=True)
        data.is_valid(raise_exception=True)
        items = {i.id: i for i in check.items.all()}
        for row in data.validated_data:
            item = items.get(row["item"])
            if item is None:
                raise ValidationError({"counts": "A line does not belong to this stock check."})
            item.counted_quantity = row["counted_quantity"]
            item.updated_by = request.user
            item.save(update_fields=["counted_quantity", "updated_by", "updated_at"])
        return Response({"saved": len(data.validated_data)})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        result = complete_verification(self.get_object(), request.user)
        log_action(request, "update", self.get_object(), changes={"completed": True, **result})
        return Response(result)


# --- Dispensing (selling) ---------------------------------------------------------------------------
class DispensingViewSet(PharmacyMixin, viewsets.ViewSet):
    """Final prescriptions of this branch, and selling against them (stock out + bill)."""

    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view", "sell": "pharmacy.dispense"}

    def _prescriptions(self, request):
        return (Prescription.objects.filter(branch=request.branch, status="final")
                .select_related("patient", "doctor", "visit__appointment").prefetch_related("items"))

    def list(self, request):
        day = _day(request.query_params.get("date"), timezone.localdate())
        wanted = request.query_params.get("status")
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
        items = list(rx.items.select_related("medicine__pack_type", "medicine__dose_unit"))
        given = dispensed_quantities(rx)
        medicine_ids = [i.medicine_id for i in items if i.medicine_id]
        batches = suggested_batches(request.branch, medicine_ids)
        locations = locations_for(request.branch, medicine_ids)
        allergies = [a.allergen for a in rx.patient.allergies.all()]
        return Response({
            "id": str(rx.id), "patient_detail": patient_summary(rx.patient), "doctor_name": rx.doctor.full_name,
            "notes": rx.notes, "status": dispense_status(rx), "allergies": allergies,
            "sales": [{"id": str(d.id), "invoice": str(d.invoice.id) if hasattr(d, "invoice") else None,
                       "number": d.invoice.number if hasattr(d, "invoice") else "", "total": str(d.total_amount)}
                      for d in rx.dispenses.all()],
            "lines": [{
                "id": str(i.id), "medicine": str(i.medicine_id) if i.medicine_id else None,
                "medicine_name": i.medicine_name, "dosage_form": i.dosage_form,
                "pack_size": i.medicine.pack_size if i.medicine else "",
                "pack_type": i.medicine.pack_type.label if i.medicine and i.medicine.pack_type_id else "",
                "allow_loose": bool(i.medicine and i.medicine.allow_loose and i.medicine.units_per_pack),
                "units_per_pack": money(i.medicine.units_per_pack) if i.medicine else None,
                "unit_label": i.medicine.dose_unit.label if i.medicine and i.medicine.dose_unit_id else "",
                "location": locations[i.medicine_id].label if i.medicine_id in locations else "",
                "dose": i.dose, "dose_unit": i.dose_unit, "frequency": i.frequency, "timing": i.timing,
                "anupana": i.anupana, "duration": i.duration, "duration_unit": i.duration_unit,
                "instructions": i.instructions, "given": money(given.get(i.id)),
                "batches": BatchSerializer(batches.get(i.medicine_id, []), many=True).data,
            } for i in items],
        })

    @action(detail=True, methods=["post"])
    def sell(self, request, pk=None):
        rx = self._prescriptions(request).filter(pk=pk).first()
        if rx is None:
            raise NotFound("Prescription not found (or not final yet).")
        data = SellInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        items = {i.id: i for i in rx.items.all()}
        lines = []
        for line in v["items"]:
            item = items.get(line["prescription_item"])
            if item is None:
                raise ValidationError({"items": "A line does not belong to this prescription."})
            if line.get("loose_units"):
                self.need_feature(request, "pharmacy_loose_sale")
            if line.get("discount_percent"):
                self.need_feature(request, "pharmacy_discounts")
            lines.append({"prescription_item": item, "batch_id": line["batch"], "quantity": line.get("quantity"),
                          "loose_units": line.get("loose_units"), "discount_percent": line.get("discount_percent", 0)})
        # Without "Pharmacy bills" the medicines are only given (stock goes down), no bill is made
        make_bill = is_feature_enabled(request.branch, "pharmacy_billing")
        record, invoice = sell(rx, request.branch, request.user, lines, notes=v.get("notes", ""),
                               payment=v.get("payment"), make_bill=make_bill)
        log_action(request, "create", invoice or record, changes={
            "patient": str(rx.patient_id), "lines": len(lines), "total": str(record.total_amount)})
        return Response({"dispense": str(record.id), "invoice": str(invoice.id) if invoice else None,
                         "number": invoice.number if invoice else "",
                         "total_amount": str(invoice.total_amount if invoice else record.total_amount),
                         "status": dispense_status(rx), "invoice_status": invoice.status if invoice else ""},
                        status=http.HTTP_201_CREATED)


class SaleViewSet(PharmacyMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Sales (dispensed prescriptions) of this branch, and sales returns."""

    required_permissions = {"list": "pharmacy.view", "retrieve": "pharmacy.view", "take_back": "pharmacy.dispense"}
    required_features = {"take_back": "pharmacy_sales_returns"}

    def get_queryset(self):
        qs = (Dispense.objects.filter(branch=self.request.branch)
              .select_related("patient", "invoice", "created_by").prefetch_related("items__medicine", "items__batch"))
        p = self.request.query_params
        if p.get("date"):
            qs = qs.filter(created_at__date=_day(p["date"]))
        if p.get("q", "").strip():
            q = p["q"].strip()
            qs = qs.filter(Q(invoice__number__icontains=q) | Q(patient__first_name__icontains=q)
                           | Q(patient__last_name__icontains=q) | Q(patient__uhid__icontains=q))
        return qs

    def _row(self, d, with_items=False):
        invoice = getattr(d, "invoice", None)
        row = {"id": str(d.id), "patient_detail": patient_summary(d.patient), "created_at": d.created_at,
               "total_amount": str(d.total_amount), "by": d.created_by.full_name if d.created_by_id else "",
               "invoice": str(invoice.id) if invoice else None, "number": invoice.number if invoice else "",
               "invoice_status": invoice.status if invoice else ""}
        if with_items:
            row["items"] = [{
                "id": str(i.id), "medicine_name": i.medicine.name, "batch_no": i.batch.batch_no,
                "quantity": str(i.quantity), "loose_units": money(i.loose_units), "returned_quantity": str(i.returned_quantity),
                "amount": str(i.amount),
            } for i in d.items.all()]
        return row

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response([self._row(d) for d in page])

    def retrieve(self, request, *args, **kwargs):
        return Response(self._row(self.get_object(), with_items=True))

    @action(detail=True, methods=["post"], url_path="return")
    def take_back(self, request, pk=None):
        dispense = self.get_object()
        data = SaleReturnInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        sold = {i.id: i for i in dispense.items.all()}
        items = []
        for line in v["items"]:
            item = sold.get(line["dispense_item"])
            if item is None:
                raise ValidationError({"items": "A line does not belong to this sale."})
            items.append({"dispense_item": item, "quantity": line["quantity"], "back_to_stock": line["back_to_stock"]})
        record, note = take_back(dispense, request.branch, request.user, items=items, reason=v["reason"],
                                 refund_mode=v["refund_mode"])
        log_action(request, "create", record, changes={"lines": len(items), "total": str(record.total_amount),
                                                        "credit_note": note.number if note else ""})
        return Response({"id": str(record.id), "total_amount": str(record.total_amount),
                         "credit_note": str(note.id) if note else None, "credit_note_number": note.number if note else "",
                         "refund_amount": str(note.refund_amount) if note else "0"}, status=http.HTTP_201_CREATED)
