"""
Clinic products: things the clinic sells that are not medicines (oils, soaps, herbal supplements, books ...).
They live in the medicine list as kind "product" and use the same stock, batches, expiry and bills as medicines.

GET  /products/?q=       products with the stock that can be sold today (earliest expiry first)
POST /products/sell/     {items: [{batch, quantity}], customer_name, customer_phone, payment}  -> bill

Needs the extra "Clinic products" (Additional settings, on by default). Doctor and receptionist can see and sell
(products.view / products.sell); adding stock is done in Pharmacy -> Purchases by people with pharmacy.stock.
Only products can be sold here: a medicine is refused (medicines are dispensed in Pharmacy).
"""
from django.db.models import Q
from rest_framework import status as http, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.audit.services import log_action
from apps.medicines.models import Medicine
from apps.medicines.services import search_filter

from .models import StockBatch
from .serializers import CounterSaleInput
from .services import counter_sell, suggested_batches
from .views import PharmacyMixin, money


class ProductViewSet(PharmacyMixin, viewsets.ViewSet):
    required_permissions = {"list": "products.view", "sell": "products.sell"}
    required_features = {"*": "clinic_products"}

    def list(self, request):
        org_id = request.user.organization_id
        products = Medicine.objects.filter(organization_id=org_id, kind="product", is_active=True)
        q = request.query_params.get("q", "").strip()
        if q:
            products = products.filter(search_filter(q) | Q(barcode=q) | Q(sku__iexact=q))
        products = list(products.order_by("name")[:200])
        batches = suggested_batches(request.branch, [p.id for p in products])
        rows = []
        for p in products:
            usable = batches.get(p.id, [])
            first = usable[0] if usable else None
            price = first.sale_price if first else (p.selling_price if p.selling_price is not None else p.mrp)
            rows.append({
                "id": str(p.id), "name": p.name, "name_gu": p.name_gu, "name_hi": p.name_hi, "pack_size": p.pack_size,
                "sku": p.sku, "barcode": p.barcode, "gst_rate": money(p.gst_rate), "price": money(price),
                "stock": str(sum((b.quantity for b in usable), 0)),
                "batches": [{"id": str(b.id), "batch_no": b.batch_no, "expiry_date": b.expiry_date,
                             "quantity": str(b.quantity), "price": money(b.sale_price)} for b in usable],
            })
        return Response(rows)

    @action(detail=False, methods=["post"])
    def sell(self, request):
        self.need_feature(request, "pharmacy_billing")
        data = CounterSaleInput(data=request.data)
        data.is_valid(raise_exception=True)
        v = data.validated_data
        ids = [line["batch"] for line in v["items"]]
        found = {b.id: b for b in StockBatch.objects.filter(branch=request.branch, id__in=ids).select_related("medicine")}
        for line in v["items"]:
            batch = found.get(line["batch"])
            if batch is None:
                raise ValidationError({"items": "A product batch was not found in this branch."})
            if batch.medicine.kind != "product":
                raise ValidationError({"items": f"{batch.medicine.name} is a medicine, not a product. "
                                                "Medicines are given in Pharmacy."})
        lines = [self._line(request, line) for line in v["items"]]
        record, invoice = counter_sell(request.branch, request.user, lines, customer_name=v.get("customer_name", ""),
                                       customer_phone=v.get("customer_phone", ""), notes=v.get("notes", ""),
                                       payment=v.get("payment"))
        log_action(request, "create", invoice, changes={"product_sale": True, "lines": len(lines), "total": str(invoice.total_amount)})
        return Response({"dispense": str(record.id), "invoice": str(invoice.id), "number": invoice.number,
                         "total_amount": str(invoice.total_amount), "invoice_status": invoice.status},
                        status=http.HTTP_201_CREATED)
