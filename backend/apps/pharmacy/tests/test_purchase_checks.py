"""Four small safety checks on stock in and counter sales: expiry required, printed total, double clicks."""
from datetime import timedelta

import pytest
from rest_framework.test import APIClient

from apps.pharmacy.models import Purchase, StockBatch
from conftest import client_for
from apps.pharmacy.tests.test_pharmacy import LATER, TODAY, meds, receive  # noqa: F401 (meds is a fixture)

pytestmark = pytest.mark.usefixtures("all_additional_features")


@pytest.mark.django_db
def test_expiry_date_is_required_when_expiry_tracking_is_on(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    res = client.post("/api/v1/purchases/", {"invoice_no": "NOEXP", "invoice_date": str(TODAY), "items": [
        {"medicine": str(meds["Triphala Churna"].id), "batch_no": "X1", "quantity": "3", "mrp": "90", "purchase_rate": "50"}]}, format="json")
    assert res.status_code == 400 and "expiry" in str(res.data).lower()
    assert not StockBatch.objects.filter(batch_no="X1").exists() and not Purchase.objects.filter(invoice_no="NOEXP").exists()


@pytest.mark.django_db
def test_printed_invoice_total_is_checked_against_the_calculated_total(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    line = [("Triphala Churna", "PT1", LATER, "10", "0", "50", "90", None)]
    # 10 x 50 = 500 + 12% GST = 560 calculated
    wrong = receive(client, meds, line, printed_total="600")
    assert wrong.status_code == 400 and "printed_total" in wrong.data and "40.00" in str(wrong.data["printed_total"])
    assert not Purchase.objects.exists() and not StockBatch.objects.filter(batch_no="PT1").exists()  # nothing was saved
    near = receive(client, meds, line, printed_total="560.60")                # within Rs 1 (rounding on the invoice)
    assert near.status_code == 201 and near.data["printed_total"] == "560.60"
    accepted = receive(client, meds, [("Triphala Churna", "PT2", LATER, "10", "0", "50", "90", None)],
                       invoice_no="INV-2", printed_total="600", accept_difference=True)
    assert accepted.status_code == 201 and accepted.data["printed_total"] == "600.00" and accepted.data["total_amount"] == "560.00"
    # leaving the printed total out still works (it is optional for the API)
    assert receive(client, meds, [("Triphala Churna", "PT3", LATER, "1")], invoice_no="INV-3").status_code == 201


@pytest.mark.django_db
def test_same_purchase_without_invoice_number_is_not_added_twice(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    body = dict(invoice_no="", invoice_date=str(TODAY))
    first = client.post("/api/v1/purchases/", {**body, "items": [{"medicine": str(meds["Triphala Churna"].id), "batch_no": "DD1",
                        "expiry_date": LATER, "quantity": "5", "mrp": "90", "purchase_rate": "50"}]}, format="json")
    assert first.status_code == 201
    again = client.post("/api/v1/purchases/", {**body, "items": [{"medicine": str(meds["Triphala Churna"].id), "batch_no": "dd1",
                        "expiry_date": LATER, "quantity": "5", "mrp": "90", "purchase_rate": "50"}]}, format="json")
    assert again.status_code == 400 and "just saved" in str(again.data)
    assert StockBatch.objects.get(batch_no="DD1").quantity == 5
    # a different quantity is a different purchase
    other = client.post("/api/v1/purchases/", {**body, "items": [{"medicine": str(meds["Triphala Churna"].id), "batch_no": "DD1",
                        "expiry_date": LATER, "quantity": "2", "mrp": "90", "purchase_rate": "50"}]}, format="json")
    assert other.status_code == 201 and StockBatch.objects.get(batch_no="DD1").quantity == 7


@pytest.mark.django_db
def test_counter_sale_double_click_makes_one_sale(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    assert receive(client, meds, [("Triphala Churna", "CS1", LATER, "10", "0", "50", "90", None)]).status_code == 201
    batch = StockBatch.objects.get(batch_no="CS1")
    sale = {"items": [{"batch": str(batch.id), "quantity": "1"}], "payment": {"mode": "cash", "amount": "90"}}
    assert client.post("/api/v1/counter-sales/", sale, format="json").status_code == 201
    second = client.post("/api/v1/counter-sales/", sale, format="json")
    assert second.status_code == 400 and "double click" in str(second.data)
    batch.refresh_from_db()
    assert batch.quantity == 9
    # a different quantity right after is a real second sale
    other = client.post("/api/v1/counter-sales/", {"items": [{"batch": str(batch.id), "quantity": "2"}]}, format="json")
    assert other.status_code == 201
