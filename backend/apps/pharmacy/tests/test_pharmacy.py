from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.emr.models import Visit
from apps.medicines.models import Medicine
from apps.medicines.services import add_sample_medicines
from apps.organizations.models import BranchFeatureFlag
from apps.pharmacy.models import StockBatch, StockMovement
from apps.patients.models import Patient
from apps.prescriptions.services import save_prescription
from conftest import client_for

TODAY = date.today()


@pytest.fixture
def meds(org, roles):
    add_sample_medicines(org)
    return {m.name: m for m in Medicine.objects.filter(organization=org)}


def purchase(client, meds, lines):
    return client.post("/api/v1/purchases/", {
        "invoice_no": "INV-1", "invoice_date": str(TODAY),
        "items": [{"medicine": str(meds[name].id), "batch_no": batch, "expiry_date": expiry, "quantity": qty,
                   "purchase_rate": "50", "mrp": "90"} for name, batch, expiry, qty in lines],
    }, format="json")


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


@pytest.mark.django_db
def test_purchase_adds_stock_and_history(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    res = purchase(client, meds, [("Triphala Churna", "tc1", str(TODAY + timedelta(days=400)), "10")])
    assert res.status_code == 201, res.data
    assert res.data["total_amount"] == "500.00"
    # Same batch again: quantity is added to the same batch
    purchase(client, meds, [("Triphala Churna", "TC1", str(TODAY + timedelta(days=400)), "5")])
    batch = StockBatch.objects.get(batch_no="TC1")
    assert batch.quantity == 15
    assert StockMovement.objects.filter(batch=batch, kind="purchase").count() == 2
    stock = client.get("/api/v1/stock/").data
    assert stock[0]["name"] == "Triphala Churna" and stock[0]["available"] == "15.00"


@pytest.mark.django_db
def test_dispense_from_prescription(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    purchase(client, meds, [
        ("Triphala Churna", "OLD", str(TODAY + timedelta(days=30)), "2"),
        ("Triphala Churna", "NEW", str(TODAY + timedelta(days=300)), "10"),
    ])
    queue = client.get("/api/v1/dispensing/").data
    assert queue[0]["id"] == str(final_rx.id) and queue[0]["status"] == "pending"
    detail = client.get(f"/api/v1/dispensing/{final_rx.id}/").data
    line = detail["lines"][0]
    assert [b["batch_no"] for b in line["batches"]] == ["OLD", "NEW"]  # earliest expiry first
    assert detail["lines"][1]["batches"] == []  # free-text line has no stock
    res = client.post(f"/api/v1/dispensing/{final_rx.id}/dispense/", {"items": [
        {"prescription_item": line["id"], "batch": line["batches"][0]["id"], "quantity": "2"}]}, format="json")
    assert res.status_code == 201, res.data
    assert res.data["total_amount"] == "180.00" and res.data["status"] == "done"
    assert StockBatch.objects.get(batch_no="OLD").quantity == 0


@pytest.mark.django_db
def test_cannot_sell_more_than_stock_or_expired(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    purchase(client, meds, [("Triphala Churna", "B1", str(TODAY + timedelta(days=300)), "1")])
    item = final_rx.items.get(medicine__isnull=False)
    batch = StockBatch.objects.get(batch_no="B1")
    url = f"/api/v1/dispensing/{final_rx.id}/dispense/"
    res = client.post(url, {"items": [{"prescription_item": str(item.id), "batch": str(batch.id), "quantity": "3"}]}, format="json")
    assert res.status_code == 400 and "only" in str(res.data)
    batch.expiry_date = TODAY - timedelta(days=1)
    batch.save()
    res = client.post(url, {"items": [{"prescription_item": str(item.id), "batch": str(batch.id), "quantity": "1"}]}, format="json")
    assert res.status_code == 400 and "expired" in str(res.data)
    assert StockBatch.objects.get(pk=batch.pk).quantity == 1  # nothing changed


@pytest.mark.django_db
def test_wrong_batch_medicine_refused(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    purchase(client, meds, [("Ashwagandha Churna", "AS1", "", "5")])
    item = final_rx.items.get(medicine__isnull=False)
    other = StockBatch.objects.get(batch_no="AS1")
    res = client.post(f"/api/v1/dispensing/{final_rx.id}/dispense/", {"items": [
        {"prescription_item": str(item.id), "batch": str(other.id), "quantity": "1"}]}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_draft_prescription_not_dispensed(pharmacist, branch_a, meds, final_rx):
    final_rx.status = "draft"
    final_rx.save()
    client = client_for(pharmacist, branch_a)
    assert client.get("/api/v1/dispensing/").data == []
    assert client.get(f"/api/v1/dispensing/{final_rx.id}/").status_code == 404


@pytest.mark.django_db
def test_adjust_needs_reason_and_low_stock(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    purchase(client, meds, [("Triphala Churna", "B1", "", "5")])
    batch = StockBatch.objects.get(batch_no="B1")
    assert client.post("/api/v1/stock/adjust/", {"batch": str(batch.id), "change": "-2", "reason": ""}, format="json").status_code == 400
    assert client.post("/api/v1/stock/adjust/", {"batch": str(batch.id), "change": "-9", "reason": "Broken"}, format="json").status_code == 400
    res = client.post("/api/v1/stock/adjust/", {"batch": str(batch.id), "change": "-2", "reason": "2 bottles broken"}, format="json")
    assert res.status_code == 200 and res.data["quantity"] == "3.00"
    client.post("/api/v1/stock/reorder-level/", {"medicine": str(meds["Triphala Churna"].id), "level": 5}, format="json")
    low = client.get("/api/v1/stock/", {"show": "low"}).data
    assert [r["name"] for r in low] == ["Triphala Churna"]
    history = client.get("/api/v1/stock/movements/", {"medicine": str(meds["Triphala Churna"].id)}).data
    assert history[0]["kind"] == "adjust" and history[0]["reason"] == "2 bottles broken"


@pytest.mark.django_db
def test_permissions_and_switch(org, doctor, receptionist, pharmacist, branch_a, meds):
    assert client_for(receptionist, branch_a).get("/api/v1/stock/").status_code == 403
    # Doctors may not add stock
    assert purchase(client_for(doctor, branch_a), meds, [("Triphala Churna", "X", "", "1")]).status_code == 403
    BranchFeatureFlag.objects.create(organization=org, branch=branch_a, code="pharmacy", enabled=False)
    res = client_for(pharmacist, branch_a).get("/api/v1/stock/")
    assert res.status_code == 403 and "switched off" in str(res.data)


@pytest.mark.django_db
def test_stock_is_per_branch(pharmacist, org, roles, branch_a, branch_b, meds):
    from conftest import make_user

    purchase(client_for(pharmacist, branch_a), meds, [("Triphala Churna", "B1", "", "5")])
    other = make_user(org, "pharma_b", {branch_b: roles["pharmacist"]})
    assert client_for(other, branch_b).get("/api/v1/stock/").data == []
