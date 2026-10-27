"""Clinic products (oils, supplements ...): doctor and receptionist sell them; medicines are refused here."""
import pytest

from apps.medicines.models import Medicine
from conftest import set_additional_features
from apps.pharmacy.models import StockBatch
from apps.pharmacy.tests.test_pharmacy import LATER, TODAY, meds, receive  # noqa: F401 (meds is a fixture)
from conftest import client_for

pytestmark = pytest.mark.usefixtures("all_additional_features")

PRODUCTS = "/api/v1/products/"


@pytest.fixture
def oil(org, meds):
    return Medicine.objects.create(organization=org, kind="product", name="Kumkumadi Face Oil", pack_size="30 ml",
                                   gst_rate=18, mrp=450, selling_price=420)


def stock(client, product, batch="KO1", qty="10"):
    res = client.post("/api/v1/purchases/", {"invoice_no": f"INV-{batch}", "invoice_date": str(TODAY), "items": [
        {"medicine": str(product.id), "batch_no": batch, "expiry_date": LATER, "quantity": qty, "purchase_rate": "250",
         "gst_rate": "18", "mrp": "450", "selling_price": "420"}]}, format="json")
    assert res.status_code == 201, res.data
    return StockBatch.objects.get(batch_no=batch)


@pytest.mark.django_db
def test_doctor_and_receptionist_see_products_and_sell_them_with_a_bill(doctor, receptionist, pharmacist, branch_a, oil):
    batch = stock(client_for(pharmacist, branch_a), oil)
    for user in (doctor, receptionist):
        rows = client_for(user, branch_a).get(PRODUCTS).data
        assert [r["name"] for r in rows] == ["Kumkumadi Face Oil"] and rows[0]["stock"] == "10.000" and rows[0]["price"] == "420.00"
    # medicines never show in the product list
    assert all(r["name"] != "Triphala Churna" for r in client_for(doctor, branch_a).get(PRODUCTS).data)

    sale = {"items": [{"batch": str(batch.id), "quantity": "2"}], "customer_name": "Kamla", "payment": {"mode": "cash", "amount": "840"}}
    res = client_for(receptionist, branch_a).post(f"{PRODUCTS}sell/", sale, format="json")
    assert res.status_code == 201, res.data
    assert res.data["total_amount"] == "840.00" and res.data["number"]
    batch.refresh_from_db()
    assert batch.quantity == 8
    res = client_for(doctor, branch_a).post(f"{PRODUCTS}sell/", {"items": [{"batch": str(batch.id), "quantity": "1"}]}, format="json")
    assert res.status_code == 201 and StockBatch.objects.get(pk=batch.pk).quantity == 7


@pytest.mark.django_db
def test_a_medicine_cannot_be_sold_through_products_and_stock_is_checked(receptionist, pharmacist, branch_a, oil, meds):
    pharma = client_for(pharmacist, branch_a)
    stock(pharma, oil)
    med = pharma.post("/api/v1/purchases/", {"invoice_no": "M1", "invoice_date": str(TODAY), "items": [
        {"medicine": str(meds["Triphala Churna"].id), "batch_no": "MED1", "expiry_date": LATER, "quantity": "5",
         "purchase_rate": "50", "mrp": "90", "gst_rate": "12"}]}, format="json")
    assert med.status_code == 201
    c = client_for(receptionist, branch_a)
    refused = c.post(f"{PRODUCTS}sell/", {"items": [{"batch": str(StockBatch.objects.get(batch_no="MED1").id), "quantity": "1"}]}, format="json")
    assert refused.status_code == 400 and "medicine" in str(refused.data).lower()
    too_many = c.post(f"{PRODUCTS}sell/", {"items": [{"batch": str(StockBatch.objects.get(batch_no="KO1").id), "quantity": "99"}]}, format="json")
    assert too_many.status_code == 400 and "left" in str(too_many.data)
    assert StockBatch.objects.get(batch_no="MED1").quantity == 5


@pytest.mark.django_db
def test_who_may_do_what_and_the_switch(doctor, receptionist, therapist, pharmacist, branch_a, oil, org):
    # the therapist has no product permission; doctor and receptionist have it by default
    assert client_for(therapist, branch_a).get(PRODUCTS).status_code == 403
    # the doctor runs the pharmacy: pharmacy stock and purchases are open to the doctor
    assert client_for(doctor, branch_a).get("/api/v1/stock/").status_code == 200
    # a receptionist cannot add stock or see the pharmacy
    assert client_for(receptionist, branch_a).get("/api/v1/stock/").status_code == 403
    # switch off: the product list and the products in the medicine list disappear
    set_additional_features(org, on=False, codes=["clinic_products"])
    assert client_for(doctor, branch_a).get(PRODUCTS).status_code == 403
    names = [m["name"] for m in client_for(doctor, branch_a).get("/api/v1/medicines/", {"q": "Kumkumadi"}).data["results"]]
    assert "Kumkumadi Face Oil" not in names
