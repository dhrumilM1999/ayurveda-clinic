"""Medicines bought on credit: what is owed to each supplier, payments, reversal, returns, opening balance."""
from datetime import timedelta

import pytest

from apps.pharmacy.models import StockBatch, Supplier, SupplierPayment
from apps.pharmacy.tests.test_pharmacy import LATER, TODAY, meds, receive  # noqa: F401 (meds is a fixture)
from conftest import client_for

pytestmark = pytest.mark.usefixtures("all_additional_features")

ACC = "/api/v1/supplier-accounts/"
PAY = "/api/v1/supplier-payments/"


@pytest.fixture
def supplier(org, branch_a):
    return Supplier.objects.create(organization=org, name="Patel Distributors", payment_terms_days=15)


def buy(client, meds, supplier, invoice_no, qty, day=TODAY, batch=None, **extra):
    """qty x Rs 50 + 12% GST: 10 packs = 560."""
    res = receive(client, meds, [("Triphala Churna", batch or f"B-{invoice_no}", LATER, str(qty), "0", "50", "90", None)],
                  supplier=str(supplier.id), invoice_no=invoice_no, invoice_date=str(day), **extra)
    assert res.status_code == 201, res.data
    return res.data


@pytest.mark.django_db
def test_credit_purchase_creates_what_is_owed_and_payments_reduce_it(pharmacist, branch_a, meds, supplier):
    c = client_for(pharmacist, branch_a)
    first = buy(c, meds, supplier, "A1", 10)
    assert (first["payable"], first["paid"], first["balance_due"], first["payment_status"]) == ("560.00", "0", "560.00", "unpaid")
    assert first["due_date"] == str(TODAY + timedelta(days=15))
    buy(c, meds, supplier, "A2", 5)  # 280
    acc = c.get(f"{ACC}{supplier.id}/").data
    assert acc["balance"] == "840.00" and acc["billed"] == "840.00" and acc["paid"] == "0"
    # a part payment: the OLDEST invoice is paid first
    res = c.post(PAY, {"supplier": str(supplier.id), "amount": "600", "mode": "upi", "reference": "UPI123"}, format="json")
    assert res.status_code == 201, res.data
    acc = c.get(f"{ACC}{supplier.id}/").data
    by_no = {i["invoice_no"]: i for i in acc["invoices"]}
    assert acc["balance"] == "240.00"
    assert (by_no["A1"]["status"], by_no["A1"]["balance"]) == ("paid", "0.00")
    assert (by_no["A2"]["status"], by_no["A2"]["balance"], by_no["A2"]["paid"]) == ("partly", "240.00", "40.00")
    assert [e["kind"] for e in acc["entries"]] == ["purchase", "purchase", "payment"] and acc["entries"][-1]["balance"] == "240.00"
    # the purchase list shows the same
    rows = {p["invoice_no"]: p for p in c.get("/api/v1/purchases/").data["results"]}
    assert rows["A2"]["payment_status"] == "partly" and rows["A1"]["balance_due"] == "0.00"
    lst = c.get(ACC).data
    assert lst["total_owed"] == "240.00" and lst["suppliers"][0]["name"] == "Patel Distributors"


@pytest.mark.django_db
def test_a_payment_can_pay_chosen_invoices_and_never_more_than_is_owed(pharmacist, branch_a, meds, supplier):
    c = client_for(pharmacist, branch_a)
    buy(c, meds, supplier, "A1", 10)
    b = buy(c, meds, supplier, "A2", 10)
    res = c.post(PAY, {"supplier": str(supplier.id), "amount": "560", "purchase_ids": [b["id"]]}, format="json")
    assert res.status_code == 201
    by_no = {i["invoice_no"]: i for i in c.get(f"{ACC}{supplier.id}/").data["invoices"]}
    assert by_no["A2"]["status"] == "paid" and by_no["A1"]["status"] == "unpaid"
    assert c.post(PAY, {"supplier": str(supplier.id), "amount": "560", "purchase_ids": [b["id"]]}, format="json").status_code == 400  # already paid
    over = c.post(PAY, {"supplier": str(supplier.id), "amount": "560.01"}, format="json")
    assert over.status_code == 400 and "only Rs 560.00 is owed" in str(over.data)
    assert c.post(PAY, {"supplier": str(supplier.id), "amount": "0"}, format="json").status_code == 400
    assert c.post(PAY, {"supplier": str(supplier.id), "amount": "10", "mode": "bitcoin"}, format="json").status_code == 400


@pytest.mark.django_db
def test_a_wrong_payment_is_reversed_with_a_reason_and_never_deleted(pharmacist, branch_a, meds, supplier):
    c = client_for(pharmacist, branch_a)
    buy(c, meds, supplier, "A1", 10)
    pid = c.post(PAY, {"supplier": str(supplier.id), "amount": "560"}, format="json").data["id"]
    assert c.get(f"{ACC}{supplier.id}/").data["balance"] == "0.00"
    assert c.post(f"{PAY}{pid}/reverse/", {"reason": ""}, format="json").status_code == 400
    assert c.post(f"{PAY}{pid}/reverse/", {"reason": "Typed the wrong supplier"}, format="json").status_code == 200
    acc = c.get(f"{ACC}{supplier.id}/").data
    assert acc["balance"] == "560.00" and acc["invoices"][0]["status"] == "unpaid"
    assert c.post(f"{PAY}{pid}/reverse/", {"reason": "again"}, format="json").status_code == 400
    assert SupplierPayment.objects.filter(pk=pid, is_reversed=True).exists()  # still there
    assert c.delete(f"{PAY}{pid}/").status_code in (404, 405)  # there is no way to delete


@pytest.mark.django_db
def test_goods_sent_back_and_the_opening_balance_change_what_is_owed(pharmacist, branch_a, meds, supplier):
    c = client_for(pharmacist, branch_a)
    assert c.post(f"{ACC}{supplier.id}/opening/", {"amount": "1000"}, format="json").status_code == 200
    buy(c, meds, supplier, "A1", 10, batch="RET1")  # 560
    assert c.get(f"{ACC}{supplier.id}/").data["balance"] == "1560.00"
    batch = StockBatch.objects.get(batch_no="RET1")
    ret = c.post("/api/v1/purchase-returns/", {"supplier": str(supplier.id), "reason": "Damaged", "reference": "CN-9",
                                               "items": [{"batch": str(batch.id), "quantity": "2"}]}, format="json")
    assert ret.status_code == 201, ret.data  # 2 x 56 = 112 credit
    acc = c.get(f"{ACC}{supplier.id}/").data
    assert acc["returned"] == "112.00" and acc["balance"] == "1448.00"
    # pay everything that is owed (the rest after the invoices clears the opening balance)
    assert c.post(PAY, {"supplier": str(supplier.id), "amount": "1448"}, format="json").status_code == 201
    assert c.get(f"{ACC}{supplier.id}/").data["balance"] == "0.00"


@pytest.mark.django_db
def test_paid_at_the_time_of_buying_and_late_invoices_show_as_overdue(pharmacist, branch_a, meds, supplier):
    c = client_for(pharmacist, branch_a)
    bought = buy(c, meds, supplier, "A1", 10, paid_now="200", paid_mode="cash")
    assert bought["paid"] == "200.00" and bought["balance_due"] == "360.00" and bought["payment_status"] == "partly"
    no_supplier = receive(c, meds, [("Triphala Churna", "NS1", LATER, "1")], paid_now="10", invoice_no="NS")
    assert no_supplier.status_code == 400 and "supplier" in str(no_supplier.data).lower()
    # an old invoice: 15 days terms, bought 50 days ago -> 35 days late
    buy(c, meds, supplier, "OLD", 10, day=TODAY - timedelta(days=50), batch="OLDB")
    acc = c.get(f"{ACC}{supplier.id}/").data
    old = next(i for i in acc["invoices"] if i["invoice_no"] == "OLD")
    assert old["days_overdue"] == 35
    assert acc["ageing"]["d31_60"] == "560.00" and acc["ageing"]["current"] == "360.00" and acc["ageing"]["overdue"] == "560.00"
    assert c.get(ACC).data["total_overdue"] == "560.00"


@pytest.mark.django_db
def test_only_stock_people_see_supplier_money_and_bad_ids_are_refused(pharmacist, receptionist, branch_a, meds, supplier):
    c = client_for(pharmacist, branch_a)
    buy(c, meds, supplier, "A1", 1)
    assert client_for(receptionist, branch_a).get(ACC).status_code == 403
    assert client_for(receptionist, branch_a).post(PAY, {"supplier": str(supplier.id), "amount": "1"}, format="json").status_code == 403
    assert c.get(f"{ACC}not-an-id/").status_code == 404
    assert c.post(PAY, {"supplier": "00000000-0000-0000-0000-000000000000", "amount": "1"}, format="json").status_code == 400


@pytest.mark.django_db
def test_purchases_from_before_the_dues_feature_are_not_counted_as_money_to_pay(pharmacist, branch_a, meds, supplier):
    from apps.pharmacy.models import Purchase

    c = client_for(pharmacist, branch_a)
    old = buy(c, meds, supplier, "OLD1", 10)
    Purchase.objects.filter(pk=old["id"]).update(in_dues=False)  # what the upgrade did to every earlier purchase
    buy(c, meds, supplier, "NEW1", 5)
    acc = c.get(f"{ACC}{supplier.id}/").data
    assert [i["invoice_no"] for i in acc["invoices"]] == ["NEW1"] and acc["balance"] == "280.00"
    rows = {p["invoice_no"]: p for p in c.get("/api/v1/purchases/").data["results"]}
    assert rows["OLD1"]["payment_status"] == "" and rows["OLD1"]["balance_due"] is None
