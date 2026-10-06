from datetime import date
from decimal import Decimal

import pytest

from apps.billing.models import Invoice
from apps.billing.pdf import rupees_in_words
from apps.billing.services import create_invoice, financial_year, line_amounts, record_payment
from apps.billing.templatetags.humanize_money import money, qty
from conftest import client_for

pytestmark = pytest.mark.usefixtures("all_additional_features")


def test_financial_year():
    assert financial_year(date(2026, 4, 1)) == "2026-27"
    assert financial_year(date(2027, 3, 31)) == "2026-27"
    assert financial_year(date(2027, 4, 1)) == "2027-28"


def test_gst_inclusive_maths():
    a = line_amounts("112", "2", "0", "12")
    assert (a["total_amount"], a["taxable_amount"], a["cgst_amount"], a["sgst_amount"]) == (
        Decimal("224.00"), Decimal("200.00"), Decimal("12.00"), Decimal("12.00"))
    d = line_amounts("100", "1", "10", "5")
    assert d["discount_amount"] == Decimal("10.00") and d["total_amount"] == Decimal("90.00")


def test_words_and_formats():
    assert rupees_in_words(Decimal("125050.50")) == "Rupees One Lakh Twenty Five Thousand Fifty and Fifty Paise Only"
    assert money("1250050.5") == "12,50,050.50"
    assert qty(Decimal("2.000")) == "2" and qty(Decimal("0.500")) == "0.5"


def simple_invoice(branch, user, price="100", quantity="1", day=None):
    return create_invoice(branch, user, series="OP", day=day, lines=[
        {"kind": "consultation", "description": "Consultation", "quantity": quantity, "unit_price": price, "gst_rate": 0}])


@pytest.mark.django_db
def test_numbers_per_branch_and_year(branch_a, branch_b, org_admin):
    first = simple_invoice(branch_a, org_admin, day=date(2026, 5, 1))
    second = simple_invoice(branch_a, org_admin, day=date(2026, 5, 2))
    other_branch = simple_invoice(branch_b, org_admin, day=date(2026, 5, 2))
    next_year = simple_invoice(branch_a, org_admin, day=date(2027, 4, 1))
    assert first.number == "A/OP/2026-27/00001" and second.number == "A/OP/2026-27/00002"
    assert other_branch.number == "B/OP/2026-27/00001"
    assert next_year.number == "A/OP/2027-28/00001"


@pytest.mark.django_db
def test_round_off_and_payments(branch_a, receptionist):
    invoice = simple_invoice(branch_a, receptionist, price="99.60")
    assert invoice.total_amount == Decimal("100.00") and invoice.round_off == Decimal("0.40")
    client = client_for(receptionist, branch_a)
    res = client.post(f"/api/v1/invoices/{invoice.id}/pay/", {"mode": "upi", "amount": "60"}, format="json")
    assert res.data["status"] == "partly_paid"
    assert client.post(f"/api/v1/invoices/{invoice.id}/pay/", {"mode": "cash", "amount": "50"}, format="json").status_code == 400
    assert client.post(f"/api/v1/invoices/{invoice.id}/pay/", {"mode": "cash", "amount": "40"}, format="json").data["status"] == "paid"
    summary = client.get("/api/v1/invoices/summary/").data
    assert summary["received"]["upi"] == "60.00" and summary["cash_in_hand"] == "40.00"


@pytest.mark.django_db
def test_cancel_makes_credit_note_and_refund(branch_a, receptionist, branch_admin):
    invoice = simple_invoice(branch_a, receptionist, price="500")
    record_payment(invoice, receptionist, mode="cash", amount=Decimal("500"))
    # Receptionist may not cancel (billing.refund); the branch admin may
    assert client_for(receptionist, branch_a).post(f"/api/v1/invoices/{invoice.id}/cancel/", {"reason": "x"}, format="json").status_code == 403
    res = client_for(branch_admin, branch_a).post(f"/api/v1/invoices/{invoice.id}/cancel/",
                                                  {"reason": "Wrong patient", "refund_mode": "cash"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "cancelled"
    note = res.data["credit_notes"][0]
    assert note["number"] == "A/CN/" + invoice.financial_year + "/00001" and note["refund_amount"] == "500.00"
    assert Invoice.objects.filter(pk=invoice.pk).exists()  # never deleted


@pytest.mark.django_db
def test_pdf_prints_and_duplicate(branch_a, receptionist):
    branch_a.upi_vpa = "clinic@okbank"
    branch_a.save()
    invoice = simple_invoice(branch_a, receptionist, price="250")
    client = client_for(receptionist, branch_a)
    for size in ("a4", "a5", "80mm"):
        res = client.get(f"/api/v1/invoices/{invoice.id}/pdf/", {"size": size})
        assert res.status_code == 200 and res.content.startswith(b"%PDF")
    invoice.refresh_from_db()
    assert invoice.print_count == 3
    upi = client.get(f"/api/v1/invoices/{invoice.id}/upi/").data
    assert upi["link"].startswith("upi://pay?pa=clinic%40okbank") and "am=250.00" in upi["link"]
