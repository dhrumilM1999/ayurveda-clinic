from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.billing.models import Invoice
from apps.emr.models import Visit
from apps.medicines.models import Medicine
from apps.medicines.services import add_sample_medicines
from apps.organizations.models import BranchFeatureFlag
from apps.patients.models import Patient
from apps.pharmacy.models import StockBatch, StockMovement
from apps.prescriptions.services import save_prescription
from conftest import client_for

TODAY = date.today()
LATER = str(TODAY + timedelta(days=400))


@pytest.fixture
def meds(org, roles):
    add_sample_medicines(org)
    return {m.name: m for m in Medicine.objects.filter(organization=org)}


def receive(client, meds, lines, **extra):
    """lines: (medicine name, batch, expiry, qty[, free, rate, mrp, selling])"""
    items = []
    for line in lines:
        name, batch, expiry, qty, *rest = line
        free, rate, mrp, selling = (rest + [0, "50", "90", None][len(rest):])[:4]
        items.append({"medicine": str(meds[name].id), "batch_no": batch, "expiry_date": expiry, "quantity": qty,
                      "free_quantity": free, "purchase_rate": rate, "mrp": mrp, "selling_price": selling,
                      "gst_rate": "12"})
    return client.post("/api/v1/purchases/", {"invoice_no": "INV-1", "invoice_date": str(TODAY), "items": items, **extra},
                       format="json")


@pytest.fixture
def final_rx(org, branch_a, doctor, meds):
    patient = Patient.objects.create(organization=org, uhid="T-1", first_name="Ramesh", last_name="Patel",
                                     gender="male", mobile="9876543210")
    visit = Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                 visit_date=timezone.localdate())
    rx = save_prescription(visit, [
        {"medicine": meds["Triphala Churna"], "medicine_name": "Triphala Churna", "dose": "3"},
        {"medicine": None, "medicine_name": "Ginger tea"},
    ], "", doctor)
    rx.status = "final"
    rx.save()
    return rx


def sell(client, rx, lines, payment=None):
    return client.post(f"/api/v1/dispensing/{rx.id}/sell/", {"items": lines, **({"payment": payment} if payment else {})},
                       format="json")


# --- Stock in ----------------------------------------------------------------------------------
@pytest.mark.django_db
def test_purchase_with_free_quantity_and_gst(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    res = receive(client, meds, [("Triphala Churna", "tc1", LATER, "10", "2", "50", "90", "85")], other_charges="5")
    assert res.status_code == 201, res.data
    # 10 x 50 = 500 taxable, GST 12% = 60, + 5 other charges = 565
    assert res.data["taxable_amount"] == "500.00" and res.data["gst_amount"] == "60.00"
    assert res.data["total_amount"] == "565.00"
    batch = StockBatch.objects.get(batch_no="TC1")
    assert batch.quantity == 12 and batch.selling_price == Decimal("85.00")
    kinds = list(StockMovement.objects.filter(batch=batch).order_by("created_at").values_list("kind", "quantity", "balance_after"))
    assert kinds == [("purchase", Decimal("10.000"), Decimal("10.000")), ("free", Decimal("2.000"), Decimal("12.000"))]


@pytest.mark.django_db
def test_purchase_checks(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    assert receive(client, meds, [("Triphala Churna", "OLD", str(TODAY - timedelta(days=1)), "1")]).status_code == 400
    assert receive(client, meds, [("Triphala Churna", "X", LATER, "1", 0, "50", "90", "95")]).status_code == 400  # selling > MRP


@pytest.mark.django_db
def test_opening_stock(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    res = client.post("/api/v1/purchases/", {"is_opening": True, "items": [
        {"medicine": str(meds["Ashwagandha Churna"].id), "batch_no": "OP1", "quantity": "4", "mrp": "120"}]}, format="json")
    assert res.status_code == 201, res.data
    assert StockMovement.objects.get(batch__batch_no="OP1").kind == "opening"


# --- Selling and billing --------------------------------------------------------------------------
@pytest.mark.django_db
def test_sell_makes_bill_with_gst(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "OLD", str(TODAY + timedelta(days=30)), "2", 0, "50", "112"),
                           ("Triphala Churna", "NEW", LATER, "10", 0, "50", "112")])
    detail = client.get(f"/api/v1/dispensing/{final_rx.id}/").data
    line = detail["lines"][0]
    assert [b["batch_no"] for b in line["batches"]] == ["OLD", "NEW"]  # FEFO
    res = sell(client, final_rx, [{"prescription_item": line["id"], "batch": line["batches"][0]["id"], "quantity": "2"}],
               payment={"mode": "cash", "amount": "224"})
    assert res.status_code == 201, res.data
    invoice = Invoice.objects.get(pk=res.data["invoice"])
    # 2 x 112 (GST included) = 224 -> taxable 200, CGST 12, SGST 12
    assert (invoice.total_amount, invoice.taxable_amount, invoice.cgst_amount, invoice.sgst_amount) == (
        Decimal("224.00"), Decimal("200.00"), Decimal("12.00"), Decimal("12.00"))
    assert invoice.status == "paid" and invoice.number.startswith("A/PH/")
    assert StockBatch.objects.get(batch_no="OLD").quantity == 0
    assert StockMovement.objects.filter(kind="dispense", reference_label=invoice.number).exists()


@pytest.mark.django_db
def test_loose_sale(pharmacist, branch_a, meds, final_rx):
    med = meds["Triphala Churna"]
    med.allow_loose, med.units_per_pack = True, Decimal("100")
    med.save()
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "1", 0, "50", "100")])
    item = final_rx.items.get(medicine__isnull=False)
    batch = StockBatch.objects.get(batch_no="B1")
    res = sell(client, final_rx, [{"prescription_item": str(item.id), "batch": str(batch.id), "loose_units": "30"}])
    assert res.status_code == 201, res.data
    assert StockBatch.objects.get(batch_no="B1").quantity == Decimal("0.7")
    assert res.data["total_amount"] == "30.00"


@pytest.mark.django_db
def test_cannot_sell_more_than_stock_or_expired(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "1")])
    item = final_rx.items.get(medicine__isnull=False)
    batch = StockBatch.objects.get(batch_no="B1")
    assert sell(client, final_rx, [{"prescription_item": str(item.id), "batch": str(batch.id), "quantity": "3"}]).status_code == 400
    batch.expiry_date = TODAY - timedelta(days=1)
    batch.save()
    res = sell(client, final_rx, [{"prescription_item": str(item.id), "batch": str(batch.id), "quantity": "1"}])
    assert res.status_code == 400 and "expired" in str(res.data)
    assert StockBatch.objects.get(pk=batch.pk).quantity == 1
    assert not Invoice.objects.exists()  # nothing half-saved


@pytest.mark.django_db
def test_sale_return_gives_credit_note_and_stock(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "5", 0, "50", "112")])
    item = final_rx.items.get(medicine__isnull=False)
    batch = StockBatch.objects.get(batch_no="B1")
    sold = sell(client, final_rx, [{"prescription_item": str(item.id), "batch": str(batch.id), "quantity": "2"}],
                payment={"mode": "upi", "amount": "224"}).data
    sale = client.get(f"/api/v1/sales/{sold['dispense']}/").data
    res = client.post(f"/api/v1/sales/{sold['dispense']}/return/", {
        "reason": "Patient had extra", "refund_mode": "cash",
        "items": [{"dispense_item": sale["items"][0]["id"], "quantity": "1", "back_to_stock": True}]}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["refund_amount"] == "112.00"
    assert StockBatch.objects.get(batch_no="B1").quantity == 4
    invoice = Invoice.objects.get(pk=sold["invoice"])
    assert invoice.credited_amount == Decimal("112.00") and invoice.status == "paid"
    # Cannot return more than was sold
    again = client.post(f"/api/v1/sales/{sold['dispense']}/return/", {
        "reason": "x", "items": [{"dispense_item": sale["items"][0]["id"], "quantity": "2"}]}, format="json")
    assert again.status_code == 400


@pytest.mark.django_db
def test_purchase_return(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "5", 0, "50", "90")])
    batch = StockBatch.objects.get(batch_no="B1")
    res = client.post("/api/v1/purchase-returns/", {"reason": "Damaged in transit", "items": [
        {"batch": str(batch.id), "quantity": "2"}]}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["total_amount"] == "112.00"  # 2 x 50 + 12% GST
    assert StockBatch.objects.get(batch_no="B1").quantity == 3


# --- Corrections, physical count, alerts, scan, ledger, location --------------------------------------
@pytest.mark.django_db
def test_corrections_need_reason(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "5")])
    batch = StockBatch.objects.get(batch_no="B1")
    url = "/api/v1/stock/adjust/"
    assert client.post(url, {"batch": str(batch.id), "change": "-2", "reason": ""}, format="json").status_code == 400
    res = client.post(url, {"batch": str(batch.id), "kind": "damaged", "change": "2", "reason": "Broken"}, format="json")
    assert res.status_code == 200 and Decimal(res.data["quantity"]) == 3  # damaged always goes out
    assert StockMovement.objects.filter(batch=batch, kind="damaged").exists()


@pytest.mark.django_db
def test_physical_stock_check(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "10"), ("Ashwagandha Churna", "A1", LATER, "4")])
    check = client.post("/api/v1/stock-checks/", {"title": "Month end"}, format="json").data
    assert check["item_count"] == 2
    assert client.post("/api/v1/stock-checks/", {}, format="json").status_code == 400  # only one open check
    items = client.get(f"/api/v1/stock-checks/{check['id']}/").data["items"]
    counts = [{"item": i["id"], "counted_quantity": "8" if i["batch_no"] == "B1" else "4"} for i in items]
    client.post(f"/api/v1/stock-checks/{check['id']}/count/", {"counts": counts}, format="json")
    res = client.post(f"/api/v1/stock-checks/{check['id']}/complete/")
    assert res.data == {"changed": 1}
    assert StockBatch.objects.get(batch_no="B1").quantity == 8
    assert StockMovement.objects.get(kind="verification").quantity == -2


@pytest.mark.django_db
def test_alerts_scan_location_ledger(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", str(TODAY + timedelta(days=20)), "3")])
    med = meds["Triphala Churna"]
    med.barcode = "8901234567890"
    med.save()
    client.post("/api/v1/stock/reorder-level/", {"medicine": str(med.id), "level": 5}, format="json")
    client.post("/api/v1/stock/reorder-level/", {"medicine": str(meds["Brahmi Ghrita"].id), "level": 2}, format="json")
    alerts = client.get("/api/v1/stock/alerts/").data
    assert alerts["low"] == 1 and alerts["expiring"] == 1 and alerts["out"] == 1  # Brahmi has none at all
    scanned = client.get("/api/v1/stock/scan/", {"code": "8901234567890"}).data
    assert scanned["name"] == "Triphala Churna" and scanned["batches"][0]["batch_no"] == "B1"
    assert client.get("/api/v1/stock/scan/", {"code": "b1"}).data["scanned_batch"]  # batch number works too
    rack = client.post("/api/v1/racks/", {"code": "a", "name": "Churna"}, format="json").data
    client.post("/api/v1/stock/location/", {"medicine": str(med.id), "rack": rack["id"], "shelf": "3"}, format="json")
    row = next(r for r in client.get("/api/v1/stock/").data if r["name"] == "Triphala Churna")
    assert row["location"] == "A-3"
    ledger = client.get("/api/v1/stock/movements/", {"medicine": str(med.id)}).data
    assert ledger["closing"] == "3.000" and ledger["by_kind"]["purchase"] == "3.000"


@pytest.mark.django_db
def test_permissions_and_switch(org, doctor, receptionist, pharmacist, branch_a, meds):
    assert client_for(receptionist, branch_a).get("/api/v1/stock/").status_code == 403
    assert receive(client_for(doctor, branch_a), meds, [("Triphala Churna", "X", LATER, "1")]).status_code == 403
    BranchFeatureFlag.objects.create(organization=org, branch=branch_a, code="pharmacy", enabled=False)
    res = client_for(pharmacist, branch_a).get("/api/v1/stock/")
    assert res.status_code == 403 and "switched off" in str(res.data)


@pytest.mark.django_db
def test_stock_is_per_branch(pharmacist, org, roles, branch_a, branch_b, meds):
    from conftest import make_user

    receive(client_for(pharmacist, branch_a), meds, [("Triphala Churna", "B1", LATER, "5")])
    other = make_user(org, "pharma_b", {branch_b: roles["pharmacist"]})
    assert client_for(other, branch_b).get("/api/v1/stock/").data == []
