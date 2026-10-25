"""
What the clinic owes its suppliers (medicines bought on credit).

  balance = opening balance + every purchase invoice (what the supplier's bill says)
            - payments made (not reversed) - medicines sent back to the supplier (purchase returns)

Each payment is matched to the oldest unpaid invoices first (or to the invoices the person chooses), so every invoice
shows how much is paid and how much is still due. Nothing is deleted: a wrong payment is reversed and then ignored.
ASK FIRST before changing the rules (they decide what the owner sees as "I owe").
"""
from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Purchase, PurchaseReturn, Supplier, SupplierOpening, SupplierPayment, SupplierPaymentAllocation

ZERO = Decimal("0")
PAISA = Decimal("0.01")
BUCKETS = [("current", 0, 0), ("d1_30", 1, 30), ("d31_60", 31, 60), ("d60_plus", 61, 100000)]  # days past the due date


def payable_of(purchase: Purchase) -> Decimal:
    """What the supplier's bill says (the printed total if it was typed, else the calculated total)."""
    return purchase.printed_total if purchase.printed_total is not None else purchase.total_amount


def due_date_of(purchase: Purchase, supplier: Supplier) -> date:
    return purchase.invoice_date + timedelta(days=supplier.payment_terms_days or 0)


def _paid_by_purchase(purchase_ids) -> dict:
    rows = (SupplierPaymentAllocation.objects.filter(purchase_id__in=purchase_ids, payment__is_reversed=False)
            .values("purchase_id").annotate(s=Sum("amount")))
    return {r["purchase_id"]: r["s"] for r in rows}


def invoices_of(branch, supplier) -> list[dict]:
    """Purchase invoices of this supplier (opening-stock entries are not invoices), oldest first."""
    purchases = list(Purchase.objects.filter(branch=branch, supplier=supplier, is_opening=False, in_dues=True).order_by("invoice_date", "created_at"))
    paid = _paid_by_purchase([p.id for p in purchases])
    today = timezone.localdate()
    rows = []
    for p in purchases:
        payable = payable_of(p)
        done = paid.get(p.id, ZERO)
        due_on = due_date_of(p, supplier)
        balance = payable - done
        rows.append({
            "id": str(p.id), "invoice_no": p.invoice_no, "invoice_date": p.invoice_date, "due_date": due_on,
            "payable": payable, "paid": done, "balance": balance,
            "days_overdue": max(0, (today - due_on).days) if balance > 0 else 0,
            "status": "paid" if balance <= 0 else ("partly" if done > 0 else "unpaid"),
        })
    return rows


def account(branch, supplier) -> dict:
    """The full account of one supplier in this branch."""
    opening = SupplierOpening.objects.filter(branch=branch, supplier=supplier).first()
    opening_amount = opening.amount if opening else ZERO
    invoices = invoices_of(branch, supplier)
    payments = list(SupplierPayment.objects.filter(branch=branch, supplier=supplier).order_by("payment_date", "created_at"))
    returns = list(PurchaseReturn.objects.filter(branch=branch, supplier=supplier).order_by("return_date", "created_at"))
    paid_total = sum((p.amount for p in payments if not p.is_reversed), ZERO)
    returned_total = sum((r.total_amount for r in returns), ZERO)
    billed = sum((i["payable"] for i in invoices), ZERO)
    balance = opening_amount + billed - paid_total - returned_total

    # One list of everything, oldest first, with the running balance
    entries = []
    if opening_amount:
        entries.append({"date": opening.created_at.date(), "sort": 0, "kind": "opening", "label": "Opening balance",
                        "debit": opening_amount, "credit": ZERO})
    for i in invoices:
        entries.append({"date": i["invoice_date"], "sort": 1, "kind": "purchase", "label": f"Invoice {i['invoice_no'] or '(no number)'}",
                        "debit": i["payable"], "credit": ZERO, "id": i["id"]})
    for p in payments:
        entries.append({"date": p.payment_date, "sort": 2, "kind": "payment", "label": f"Payment ({p.get_mode_display()}){' ' + p.reference if p.reference else ''}",
                        "debit": ZERO, "credit": p.amount, "id": str(p.id), "reversed": p.is_reversed})
    for r in returns:
        entries.append({"date": r.return_date, "sort": 3, "kind": "return", "label": f"Returned to supplier{' ' + r.reference if r.reference else ''}",
                        "debit": ZERO, "credit": r.total_amount, "id": str(r.id)})
    entries.sort(key=lambda e: (e["date"], e["sort"]))
    running = ZERO
    for e in entries:
        if not e.get("reversed"):
            running += e["debit"] - e["credit"]
        e["balance"] = running
    return {
        "supplier": supplier, "opening": opening_amount, "billed": billed, "paid": paid_total, "returned": returned_total,
        "balance": balance, "invoices": invoices, "entries": entries, "payments": payments,
        "ageing": ageing(invoices, balance),
    }


def ageing(invoices, balance) -> dict:
    """How much of the unpaid invoices is not yet due, or late by 1-30, 31-60, 61+ days. 'other' = opening balance and credits."""
    result = {key: ZERO for key, _, _ in BUCKETS}
    for i in invoices:
        if i["balance"] <= 0:
            continue
        for key, low, high in BUCKETS:
            if low <= i["days_overdue"] <= high:
                result[key] += i["balance"]
                break
    result["other"] = balance - sum(result.values(), ZERO)
    result["overdue"] = result["d1_30"] + result["d31_60"] + result["d60_plus"]
    return result


def all_accounts(branch) -> list[dict]:
    """One line per supplier that has any purchase, payment, return or opening balance in this branch."""
    ids = set(Purchase.objects.filter(branch=branch, supplier__isnull=False, is_opening=False, in_dues=True).values_list("supplier_id", flat=True))
    ids |= set(SupplierOpening.objects.filter(branch=branch).values_list("supplier_id", flat=True))
    ids |= set(SupplierPayment.objects.filter(branch=branch).values_list("supplier_id", flat=True))
    ids |= set(PurchaseReturn.objects.filter(branch=branch, supplier__isnull=False).values_list("supplier_id", flat=True))
    rows = []
    for supplier in Supplier.objects.filter(organization_id=branch.organization_id, id__in=ids).order_by("name"):
        a = account(branch, supplier)
        last = max((p.payment_date for p in a["payments"] if not p.is_reversed), default=None)
        rows.append({"supplier": supplier, "balance": a["balance"], "billed": a["billed"], "paid": a["paid"],
                     "ageing": a["ageing"], "last_payment": last})
    return rows


@transaction.atomic
def set_opening_balance(branch, user, supplier, amount) -> SupplierOpening:
    if amount < 0:
        raise ValidationError({"amount": "The opening balance cannot be negative."})
    row = SupplierOpening.objects.select_for_update().filter(branch=branch, supplier=supplier).first()
    if row is None:
        row = SupplierOpening(organization_id=branch.organization_id, branch=branch, supplier=supplier, created_by=user)
    row.amount, row.updated_by = amount, user
    row.save()
    return row


@transaction.atomic
def record_payment(branch, user, *, supplier, amount, mode="cash", payment_date=None, reference="", notes="",
                   purchase_ids=None) -> SupplierPayment:
    """
    Pay a supplier. The amount goes to the chosen invoices (in the order given) or, if none chosen, to the oldest
    unpaid invoices first; whatever is left clears the opening balance. More than is owed is refused.
    """
    amount = Decimal(amount).quantize(PAISA)
    if amount <= 0:
        raise ValidationError({"amount": "The amount must be more than 0."})
    if mode not in dict(SupplierPayment.MODES):
        raise ValidationError({"mode": "Choose how it was paid."})
    # One payment at a time per supplier (two people paying at the same moment must not both see the same balance)
    Supplier.objects.select_for_update().filter(pk=supplier.pk).first()
    state = account(branch, supplier)
    if amount > state["balance"]:
        raise ValidationError({"amount": f"{supplier.name}: only Rs {state['balance']:.2f} is owed. The payment is more than that."})

    open_invoices = {i["id"]: i for i in state["invoices"] if i["balance"] > 0}
    if purchase_ids:
        chosen = []
        for pid in purchase_ids:
            invoice = open_invoices.get(str(pid))
            if invoice is None:
                raise ValidationError({"purchase_ids": "A chosen invoice is not found or is already paid."})
            chosen.append(invoice)
    else:
        chosen = list(open_invoices.values())  # oldest first
    payment = SupplierPayment.objects.create(
        organization_id=branch.organization_id, branch=branch, supplier=supplier, payment_date=payment_date or timezone.localdate(),
        amount=amount, mode=mode, reference=reference[:60], notes=notes[:300], created_by=user, updated_by=user,
    )
    left = amount
    for invoice in chosen:
        if left <= 0:
            break
        part = min(left, invoice["balance"])
        SupplierPaymentAllocation.objects.create(organization_id=branch.organization_id, payment=payment,
                                                 purchase_id=invoice["id"], amount=part, created_by=user, updated_by=user)
        left -= part
    # What is left (nothing chosen to pay it) clears the opening balance / earlier dues; it can never exceed the balance
    return payment


@transaction.atomic
def reverse_payment(payment: SupplierPayment, user, reason) -> SupplierPayment:
    if not reason.strip():
        raise ValidationError({"reason": "Please write why this payment is reversed."})
    payment = SupplierPayment.objects.select_for_update().get(pk=payment.pk)
    if payment.is_reversed:
        raise ValidationError({"detail": "This payment is already reversed."})
    payment.is_reversed = True
    payment.reversed_at = timezone.now()
    payment.reversed_by = user
    payment.reverse_reason = reason[:200]
    payment.updated_by = user
    payment.save()
    return payment
