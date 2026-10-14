"""Pharmacy reports: what to buy, daily, top selling, slow items, margin, GST."""
import pytest

from apps.pharmacy.models import StockBatch
from apps.pharmacy.tests.test_pharmacy import LATER, TODAY, meds, receive  # noqa: F401 (fixtures)
from conftest import client_for, set_additional_features

pytestmark = pytest.mark.usefixtures("all_additional_features")
URL = "/api/v1/pharmacy-reports/"


def counter_sale(client, meds, qty="2"):
    batch = StockBatch.objects.get(batch_no="B1")
    return client.post("/api/v1/counter-sales/", {"items": [{"batch": str(batch.id), "quantity": qty}],
                                                  "payment": {"mode": "cash", "amount": "500"}}, format="json")


@pytest.mark.django_db
def test_reports_are_off_until_switched_on(org, pharmacist, branch_a):
    set_additional_features(org, on=False, codes=["pharmacy_reports"])
    assert client_for(pharmacist, branch_a).get(URL).status_code == 403


@pytest.mark.django_db
def test_reorder_list_suggests_a_quantity(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "3")])
    medicine = meds["Triphala Churna"]
    assert client.post("/api/v1/stock/reorder-level/", {"medicine": str(medicine.id), "level": "5"}, format="json").status_code == 200
    rows = client.get(URL + "reorder/").data["rows"]
    assert [r["name"] for r in rows] == ["Triphala Churna"]
    assert rows[0]["suggested"] == 7  # twice the level (10) minus 3 in stock


@pytest.mark.django_db
def test_daily_top_selling_margin_and_gst(pharmacist, branch_a, meds):
    client = client_for(pharmacist, branch_a)
    receive(client, meds, [("Triphala Churna", "B1", LATER, "10", 0, "50", "90", "90")])
    assert counter_sale(client, meds).status_code == 201
    daily = client.get(URL + "daily/").data
    assert daily["rows"][0]["bills"] == 1 and str(daily["rows"][0]["billed"]) == "180.00"
    assert str(daily["rows"][0]["cash"]) == "180.00" and daily["rows"][0]["purchases"] > 0
    top = client.get(URL + "top_selling/").data["rows"]
    assert top[0]["name"] == "Triphala Churna" and top[0]["qty"] == 2
    margin = client.get(URL + "margin/").data["rows"][0]
    # 2 packs sold for 180 with 12% GST: 160.71 without GST, bought for 100
    assert str(margin["sales"]) == "160.71" and str(margin["cost"]) == "100.00"
    gst = client.get(URL + "gst/").data
    assert str(gst["totals"]["tax"]) == "19.29"
    # Medicine in stock and sold today is not "non-moving"
    assert client.get(URL + "non_moving/").data["rows"] == []


@pytest.mark.django_db
def test_money_reports_need_billing_permission(therapist, org, branch_a):
    set_additional_features(org, codes=["pharmacy_reports"])
    client = client_for(therapist, branch_a)
    # A therapist has no pharmacy.view at all
    assert client.get(URL + "daily/").status_code == 403
