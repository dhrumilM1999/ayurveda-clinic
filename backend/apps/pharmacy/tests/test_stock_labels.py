"""Pharmacy stock labels (barcode, no patient details), scanning them, extra scanned medicines and counter sales."""
from decimal import Decimal

import pytest

from apps.audit.models import AuditLog
from apps.billing.models import Invoice
from apps.pharmacy.models import Dispense, StockBatch
from apps.pharmacy.tests.test_pharmacy import LATER, final_rx, meds, receive, sell  # noqa: F401 (fixtures)
from conftest import client_for, set_additional_features

pytestmark = pytest.mark.usefixtures("all_additional_features")


def labels(client, items, **params):
    return client.get("/api/v1/stock/labels/", {"items": ",".join(f"{b.id}:{n}" for b, n in items), **params})


@pytest.mark.django_db
def test_stock_labels_give_a_batch_a_barcode_that_scans(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC9", LATER, "3")])
    batch = StockBatch.objects.get(batch_no="TC9")
    assert batch.barcode == ""
    res = labels(client, [(batch, 3)], layout="compact")
    assert res.status_code == 200 and res.content[:4] == b"%PDF"
    batch.refresh_from_db()
    assert len(batch.barcode) == 12 and batch.barcode.startswith("29")
    # Printing again keeps the same code
    labels(client, [(batch, 1)], layout="standard")
    first = batch.barcode
    batch.refresh_from_db()
    assert batch.barcode == first
    # The scanner finds that exact batch
    found = client.get("/api/v1/stock/scan/", {"code": first}).data
    assert found["scanned_batch"] == str(batch.id)
    assert AuditLog.objects.filter(action="print", object_type="pharmacy.stocklabel").count() == 2


@pytest.mark.django_db
def test_maker_barcode_is_kept(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC8", LATER, "1")])
    batch = StockBatch.objects.get(batch_no="TC8")
    batch.barcode = "8901234567890"
    batch.save()
    assert labels(client, [(batch, 1)]).status_code == 200
    batch.refresh_from_db()
    assert batch.barcode == "8901234567890"


@pytest.mark.django_db
def test_stock_labels_need_their_switch_and_a_sane_count(org, pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC7", LATER, "1")])
    batch = StockBatch.objects.get(batch_no="TC7")
    assert labels(client, [(batch, 501)]).status_code == 400
    assert labels(client, [(batch, 0)]).status_code == 400
    set_additional_features(org, on=False, codes=["pharmacy_stock_labels"])
    assert labels(client, [(batch, 1)]).status_code == 403


# --- Scanned medicine that is not on the prescription ---------------------------------------------------
@pytest.mark.django_db
def test_scanned_extra_medicine_goes_on_the_same_bill(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC1", LATER, "5", 0, "50", "90"),
                           ("Ashwagandha Churna", "AS1", LATER, "4", 0, "60", "120")])
    line = client.get(f"/api/v1/dispensing/{final_rx.id}/").data["lines"][0]
    extra = StockBatch.objects.get(batch_no="AS1")
    res = sell(client, final_rx, [
        {"prescription_item": line["id"], "batch": line["batches"][0]["id"], "quantity": "1"},
        {"prescription_item": None, "batch": str(extra.id), "quantity": "2"},
    ], payment={"mode": "cash", "amount": "330"})
    assert res.status_code == 201, res.data
    invoice = Invoice.objects.get(pk=res.data["invoice"])
    assert invoice.total_amount == Decimal("330.00") and invoice.status == "paid"  # 90 + 2 x 120
    assert invoice.lines.count() == 2
    extra.refresh_from_db()
    assert extra.quantity == 2
    assert res.data["status"] == "done"  # the prescription itself is fully given


@pytest.mark.django_db
def test_schedule_e1_is_never_sold_without_a_prescription(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Arogyavardhini Vati", "AV1", LATER, "3", 0, "80", "150")])
    batch = StockBatch.objects.get(batch_no="AV1")
    res = sell(client, final_rx, [{"prescription_item": None, "batch": str(batch.id), "quantity": "1"}])
    assert res.status_code == 400 and "Schedule E1" in str(res.data)
    counter = client.post("/api/v1/counter-sales/", {"items": [{"batch": str(batch.id), "quantity": "1"}]}, format="json")
    assert counter.status_code == 400 and "Schedule E1" in str(counter.data)
    batch.refresh_from_db()
    assert batch.quantity == 3


# --- Counter sale ----------------------------------------------------------------------------------------
@pytest.mark.django_db
def test_counter_sale_bills_a_walk_in_customer(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC2", LATER, "5", 0, "50", "90")])
    batch = StockBatch.objects.get(batch_no="TC2")
    labels(client, [(batch, 1)])  # gives the batch a barcode
    batch.refresh_from_db()
    scanned = client.get("/api/v1/stock/scan/", {"code": batch.barcode}).data
    res = client.post("/api/v1/counter-sales/", {
        "customer_name": "Mehul", "customer_phone": "9812345621",
        "items": [{"batch": scanned["scanned_batch"], "quantity": "2"}],
        "payment": {"mode": "upi", "amount": "180", "reference": "UPI123"},
    }, format="json")
    assert res.status_code == 201, res.data
    invoice = Invoice.objects.get(pk=res.data["invoice"])
    assert invoice.series == "PH" and invoice.patient is None and invoice.customer_name == "Mehul"
    assert invoice.total_amount == Decimal("180.00") and invoice.status == "paid"
    sale = Dispense.objects.get(pk=res.data["dispense"])
    assert sale.prescription is None and sale.customer_phone == "9812345621"
    batch.refresh_from_db()
    assert batch.quantity == 3
    # The Sales list shows it as a counter sale with a masked phone; it can be returned like any sale
    row = client.get("/api/v1/sales/", {"q": "Mehul"}).data["results"][0]
    assert row["counter_sale"] is True and row["patient_detail"] is None and row["customer_phone"] == "98XXXXXX21"
    item = client.get(f"/api/v1/sales/{sale.id}/").data["items"][0]
    back = client.post(f"/api/v1/sales/{sale.id}/return/", {"reason": "Not needed", "refund_mode": "cash",
                                                              "items": [{"dispense_item": item["id"], "quantity": "1"}]},
                       format="json")
    assert back.status_code == 201, back.data
    batch.refresh_from_db()
    assert batch.quantity == 4


@pytest.mark.django_db
def test_counter_sale_without_name_and_its_switch(org, pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "TC3", LATER, "2", 0, "50", "90")])
    batch = StockBatch.objects.get(batch_no="TC3")
    res = client.post("/api/v1/counter-sales/", {"items": [{"batch": str(batch.id), "quantity": "1"}]}, format="json")
    assert res.status_code == 201
    assert Invoice.objects.get(pk=res.data["invoice"]).customer_name == "Walk-in customer"
    assert client.post("/api/v1/counter-sales/", {"items": []}, format="json").status_code == 400
    bad_phone = client.post("/api/v1/counter-sales/", {"customer_phone": "12", "items": [
        {"batch": str(batch.id), "quantity": "1"}]}, format="json")
    assert bad_phone.status_code == 400
    set_additional_features(org, on=False, codes=["pharmacy_counter_sale"])
    assert client.post("/api/v1/counter-sales/", {"items": [{"batch": str(batch.id), "quantity": "1"}]},
                       format="json").status_code == 403
