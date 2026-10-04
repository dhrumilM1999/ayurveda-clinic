"""The extra pharmacy features are off until an organization admin switches them on (Additional settings)."""
from datetime import timedelta

import pytest

from apps.billing.models import Invoice
from apps.pharmacy.models import StockBatch
from apps.pharmacy.tests.test_pharmacy import LATER, TODAY, final_rx, meds, receive, sell  # noqa: F401 (fixtures)
from conftest import client_for, set_additional_features


@pytest.mark.django_db
def test_basic_pharmacy_works_with_all_extras_off(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    assert receive(client, meds, [("Triphala Churna", "B1", LATER, "5")]).status_code == 201
    line = client.get(f"/api/v1/dispensing/{final_rx.id}/").data["lines"][0]
    res = sell(client, final_rx, [{"prescription_item": line["id"], "batch": line["batches"][0]["id"], "quantity": "2"}])
    # Medicines are given and stock goes down, but no bill is made
    assert res.status_code == 201, res.data
    assert res.data["invoice"] is None and res.data["number"] == ""
    assert not Invoice.objects.exists()
    assert StockBatch.objects.get(batch_no="B1").quantity == 3
    # Stock list, corrections and stock history stay available
    assert client.get("/api/v1/stock/").status_code == 200
    assert client.get("/api/v1/stock/movements/").status_code == 200


@pytest.mark.django_db
def test_extras_are_refused_while_off(pharmacist, branch_a, meds, final_rx):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "5")])
    assert client.get("/api/v1/racks/").status_code == 403
    assert client.get("/api/v1/stock-checks/").status_code == 403
    assert client.get("/api/v1/purchase-returns/").status_code == 403
    assert client.get("/api/v1/stock/alerts/").status_code == 403
    assert client.get("/api/v1/stock/scan/", {"code": "B1"}).status_code == 403
    opening = client.post("/api/v1/purchases/", {"is_opening": True, "items": [
        {"medicine": str(meds["Triphala Churna"].id), "batch_no": "OP", "quantity": "1", "mrp": "90"}]}, format="json")
    assert opening.status_code == 403
    line = client.get(f"/api/v1/dispensing/{final_rx.id}/").data["lines"][0]
    batch = line["batches"][0]["id"]
    discounted = sell(client, final_rx, [{"prescription_item": line["id"], "batch": batch, "quantity": "1",
                                          "discount_percent": "10"}])
    assert discounted.status_code == 403
    loose = sell(client, final_rx, [{"prescription_item": line["id"], "batch": batch, "loose_units": "10"}])
    assert loose.status_code == 403


@pytest.mark.django_db
def test_switching_on_one_extra_enables_only_that_one(org, pharmacist, branch_a, meds):
    set_additional_features(org, codes=["pharmacy_racks"])
    client = client_for(pharmacist, branch_a)
    assert client.get("/api/v1/racks/").status_code == 200
    assert client.get("/api/v1/stock-checks/").status_code == 403


@pytest.mark.django_db
def test_sale_return_without_bills(org, pharmacist, branch_a, meds, final_rx):
    set_additional_features(org, codes=["pharmacy_sales_returns"])
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", str(TODAY + timedelta(days=300)), "5")])
    line = client.get(f"/api/v1/dispensing/{final_rx.id}/").data["lines"][0]
    sale = sell(client, final_rx, [{"prescription_item": line["id"], "batch": line["batches"][0]["id"], "quantity": "2"}])
    item = client.get(f"/api/v1/sales/{sale.data['dispense']}/").data["items"][0]
    res = client.post(f"/api/v1/sales/{sale.data['dispense']}/return/", {
        "reason": "Changed medicine", "items": [{"dispense_item": item["id"], "quantity": "1", "back_to_stock": True}]},
        format="json")
    assert res.status_code == 201, res.data
    assert res.data["credit_note"] is None  # no bill, so no credit note
    assert StockBatch.objects.get(batch_no="B1").quantity == 4
