"""
Billing rules: invoice numbers, GST maths (prices include GST), payments, credit notes, day summary.
Other modules (pharmacy, OPD) create bills through these functions.
"""
from datetime import date as date_cls
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import CreditNote, CreditNoteLine, DocumentSequence, Invoice, InvoiceLine, Payment

PAISA = Decimal("0.01")
RUPEE = Decimal("1")
ZERO = Decimal("0")


def rupees(value) -> Decimal:
    return Decimal(value).quantize(PAISA, rounding=ROUND_HALF_UP)


def financial_year(day: date_cls) -> str:
    """April-March: 5 May 2026 -> "2026-27", 10 Feb 2027 -> "2026-27"."""
    start = day.year if day.month >= 4 else day.year - 1
    return f"{start}-{str(start + 1)[2:]}"


def next_number(branch, series: str, day: date_cls) -> tuple[str, str]:
    """Next document number, e.g. MAIN/PH/2026-27/00001. Must be called inside a transaction."""
    fy = financial_year(day)
    DocumentSequence.objects.get_or_create(branch=branch, series=series, financial_year=fy)
    seq = DocumentSequence.objects.select_for_update().get(branch=branch, series=series, financial_year=fy)
    seq.last_number += 1
    seq.save(update_fields=["last_number"])
    return f"{branch.code}/{series}/{fy}/{seq.last_number:05d}", fy


def line_amounts(unit_price, quantity, discount_percent, gst_rate) -> dict:
    """
    Price includes GST. Example: 2 x ₹112 with 12% GST, no discount -> total 224.00,
    taxable 200.00, CGST 12.00, SGST 12.00.
    """
    unit_price, quantity = Decimal(unit_price), Decimal(quantity)
    discount_percent, gst_rate = Decimal(discount_percent or 0), Decimal(gst_rate or 0)
    gross = rupees(unit_price * quantity)
    discount = rupees(gross * discount_percent / 100)
    total = gross - discount
    taxable = rupees(total * 100 / (100 + gst_rate))
    gst = total - taxable
    cgst = rupees(gst / 2)
    return {"gross_amount": gross, "discount_amount": discount, "taxable_amount": taxable,
            "cgst_amount": cgst, "sgst_amount": gst - cgst, "total_amount": total}


def refresh_status(invoice: Invoice):
    net_due = invoice.total_amount - invoice.credited_amount
    net_paid = invoice.paid_amount - invoice.refunded_amount
    if invoice.credited_amount > 0 and net_due <= 0:
        invoice.status = "cancelled"
    elif net_paid >= net_due:
        invoice.status = "paid"
    elif net_paid > 0:
        invoice.status = "partly_paid"
    else:
        invoice.status = "unpaid"


def _add_line(invoice: Invoice, line: dict, user, order: int) -> InvoiceLine:
    amounts = line_amounts(line["unit_price"], line["quantity"], line.get("discount_percent", 0), line.get("gst_rate", 0))
    return InvoiceLine.objects.create(
        organization_id=invoice.organization_id, invoice=invoice, kind=line.get("kind", "medicine"),
        description=line["description"][:250], medicine=line.get("medicine"), batch=line.get("batch"),
        service=line.get("service"), dispense_item=line.get("dispense_item"), batch_no=line.get("batch_no", ""),
        expiry_date=line.get("expiry_date"), hsn_code=line.get("hsn_code", ""), quantity=line["quantity"],
        unit_label=line.get("unit_label", ""), unit_price=line["unit_price"],
        discount_percent=line.get("discount_percent", 0), gst_rate=line.get("gst_rate", 0), sort_order=order,
        created_by=user, updated_by=user, **amounts,
    )


def _recalculate(invoice: Invoice):
    """Bill totals from all its lines; the total is rounded to the rupee (round-off shown on the bill)."""
    totals = {k: ZERO for k in ("gross_amount", "discount_amount", "taxable_amount", "cgst_amount", "sgst_amount")}
    for line in invoice.lines.all():
        for key in totals:
            totals[key] += getattr(line, key)
    exact = totals["taxable_amount"] + totals["cgst_amount"] + totals["sgst_amount"]
    rounded = exact.quantize(RUPEE, rounding=ROUND_HALF_UP).quantize(PAISA)
    for key, value in totals.items():
        setattr(invoice, key, value)
    invoice.round_off = rounded - exact
    invoice.total_amount = rounded
    refresh_status(invoice)


@transaction.atomic
def create_invoice(branch, user, *, series, lines: list[dict], patient=None, prescription=None, dispense=None,
                   customer_name="", notes="", day=None, care_type=None, doctor=None, appointment=None,
                   visit=None) -> Invoice:
    """
    lines: [{"kind", "description", "quantity", "unit_price", "gst_rate", "discount_percent", "unit_label",
             "hsn_code", "medicine", "batch", "batch_no", "expiry_date", "dispense_item", "service"}]
    """
    if not lines:
        raise ValidationError({"lines": "A bill needs at least one line."})
    day = day or timezone.localdate()
    number, fy = next_number(branch, series, day)
    invoice = Invoice.objects.create(
        organization_id=branch.organization_id, branch=branch, number=number, series=series, financial_year=fy,
        care_type=care_type or ("OPD" if series == "OP" else "PHARMACY"), invoice_date=day, patient=patient,
        prescription=prescription, dispense=dispense, doctor=doctor, appointment=appointment, visit=visit,
        customer_name=customer_name or (patient.full_name if patient else ""), place_of_supply=branch.state,
        notes=notes[:300], created_by=user, updated_by=user,
    )
    for order, line in enumerate(lines):
        _add_line(invoice, line, user, order)
    _recalculate(invoice)
    invoice.save()
    return invoice


@transaction.atomic
def add_lines(invoice: Invoice, user, lines: list[dict]) -> Invoice:
    """Add more lines to an open bill (e.g. services after the check-up). A cancelled bill cannot change."""
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if invoice.status == "cancelled":
        raise ValidationError({"detail": "This bill is cancelled. Make a new bill."})
    if not lines:
        raise ValidationError({"lines": "Add at least one line."})
    start = invoice.lines.count()
    for order, line in enumerate(lines):
        _add_line(invoice, line, user, start + order)
    _recalculate(invoice)
    invoice.updated_by = user
    invoice.save()
    return invoice


@transaction.atomic
def record_payment(invoice: Invoice, user, *, mode: str, amount, reference="") -> Payment:
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    amount = rupees(amount)
    if invoice.status == "cancelled":
        raise ValidationError({"detail": "This bill is cancelled."})
    if amount <= 0:
        raise ValidationError({"amount": "Amount must be more than 0."})
    if amount > invoice.balance:
        raise ValidationError({"amount": f"Only {invoice.balance} is due on this bill."})
    payment = Payment.objects.create(
        organization_id=invoice.organization_id, branch_id=invoice.branch_id, invoice=invoice, mode=mode, amount=amount,
        reference=reference[:100], paid_at=timezone.now(), created_by=user, updated_by=user,
    )
    invoice.paid_amount += amount
    refresh_status(invoice)
    invoice.updated_by = user
    invoice.save(update_fields=["paid_amount", "status", "updated_by", "updated_at"])
    return payment


@transaction.atomic
def create_credit_note(invoice: Invoice, user, *, items: list[tuple], reason: str, refund_mode: str = "cash",
                       sale_return=None) -> CreditNote:
    """
    items: [(InvoiceLine, quantity)] - the quantities taken back. Amounts are in proportion to the line.
    Money is refunded only up to what was actually paid; the rest just reduces what is due.
    """
    invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    if not reason.strip():
        raise ValidationError({"reason": "Please write the reason."})
    if not items:
        raise ValidationError({"items": "Choose what is returned."})
    day = timezone.localdate()
    number, fy = next_number(invoice.branch, "CN", day)
    note = CreditNote.objects.create(
        organization_id=invoice.organization_id, branch_id=invoice.branch_id, number=number, financial_year=fy,
        note_date=day, invoice=invoice, sale_return=sale_return, reason=reason[:200], refund_mode=refund_mode,
        created_by=user, updated_by=user,
    )
    totals = {"taxable_amount": ZERO, "cgst_amount": ZERO, "sgst_amount": ZERO, "total_amount": ZERO}
    for line, quantity in items:
        line = InvoiceLine.objects.select_for_update().get(pk=line.pk)
        left = line.quantity - line.credited_quantity
        if quantity <= 0 or quantity > left:
            raise ValidationError({"items": f"{line.description}: only {left} can be returned."})
        share = Decimal(quantity) / line.quantity
        amounts = {k: rupees(getattr(line, k) * share) for k in totals}
        CreditNoteLine.objects.create(organization_id=invoice.organization_id, credit_note=note, invoice_line=line,
                                      quantity=quantity, created_by=user, updated_by=user, **amounts)
        line.credited_quantity += quantity
        line.save(update_fields=["credited_quantity"])
        for key in totals:
            totals[key] += amounts[key]
    for key, value in totals.items():
        setattr(note, key, value)
    paid_now = invoice.paid_amount - invoice.refunded_amount
    still_due_before = invoice.total_amount - invoice.credited_amount
    # Refund only what was overpaid after this credit
    refund = max(ZERO, paid_now - (still_due_before - note.total_amount))
    refund = min(refund, note.total_amount)
    note.refund_amount = refund
    if refund == 0:
        note.refund_mode = "none"
    note.save()
    invoice.credited_amount += note.total_amount
    invoice.refunded_amount += refund
    refresh_status(invoice)
    if invoice.status == "cancelled" and invoice.cancelled_at is None:
        invoice.cancelled_at = timezone.now()
        invoice.cancel_reason = reason[:200]
    invoice.updated_by = user
    invoice.save()
    return note


def day_summary(branch, day: date_cls) -> dict:
    """Daily closing: bills made, money received by mode, refunds by mode, cash in hand."""
    invoices = Invoice.objects.filter(branch=branch, invoice_date=day)
    payments = Payment.objects.filter(branch=branch, paid_at__date=day)
    notes = CreditNote.objects.filter(branch=branch, note_date=day)
    by_mode = {m: rupees(payments.filter(mode=m).aggregate(s=Sum("amount"))["s"] or 0) for m in ("cash", "upi", "card")}
    refunds = {m: rupees(notes.filter(refund_mode=m).aggregate(s=Sum("refund_amount"))["s"] or 0) for m in ("cash", "upi", "card")}
    agg = invoices.aggregate(count=Count("id"), total=Sum("total_amount"), taxable=Sum("taxable_amount"),
                             cgst=Sum("cgst_amount"), sgst=Sum("sgst_amount"), discount=Sum("discount_amount"))
    due = sum((i.balance for i in invoices.exclude(status__in=["paid", "cancelled"])), ZERO)
    return {
        "date": str(day),
        "invoice_count": agg["count"],
        "billed": rupees(agg["total"] or 0), "taxable": rupees(agg["taxable"] or 0),
        "cgst": rupees(agg["cgst"] or 0), "sgst": rupees(agg["sgst"] or 0), "discount": rupees(agg["discount"] or 0),
        "received": by_mode, "refunds": refunds,
        "credit_notes": notes.count(), "credited": rupees(notes.aggregate(s=Sum("total_amount"))["s"] or 0),
        "cash_in_hand": by_mode["cash"] - refunds["cash"],
        "still_due": rupees(due),
    }


def invoice_for_dispense(dispense) -> Invoice | None:
    """The bill of a pharmacy sale: its own pharmacy bill, or the OPD bill it was added to (combined bill)."""
    own = Invoice.objects.filter(dispense=dispense).first()
    if own:
        return own
    line = InvoiceLine.objects.filter(dispense_item__dispense=dispense).select_related("invoice").first()
    return line.invoice if line else None
