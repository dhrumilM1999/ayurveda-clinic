"""
Financial-year and GST reports (read-only), same shape as reports.py:
    {"columns": [{"key", "label", "type"}], "rows": [{...}], "totals": {...} or None}

- gst_payable     GST to pay: tax on sales (minus credit notes) against tax paid on purchases, per GST rate
- fy_summary      month by month (choose a financial year, 1 April - 31 March)
- sales_register  every bill and credit note in order (what the CA asks for)
- purchase_register every supplier invoice in order, with the supplier's GSTIN
- dues            bills with money still to be paid

These are a guide. Your CA files the GST return - confirm the figures with them.
"""
from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.billing.models import CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment
from apps.common.utils import mask_phone

from .reports import _period_key, _totals, col

ZERO = Decimal("0")


def _who(invoice):
    if invoice.patient_id:
        return invoice.patient.full_name
    return invoice.customer_name or "Counter sale"


def gst_payable(branches, date_from, date_to, grouping=None):
    """Per GST rate: tax charged on sales (minus credit notes) against tax paid on purchases.
    Opening stock is not a purchase. Purchase returns and IGST are not taken off."""
    from apps.pharmacy.models import PurchaseItem

    lines = InvoiceLine.objects.filter(invoice__branch__in=branches, invoice__invoice_date__gte=date_from,
                                       invoice__invoice_date__lte=date_to)
    credits = CreditNoteLine.objects.filter(credit_note__branch__in=branches, credit_note__note_date__gte=date_from,
                                            credit_note__note_date__lte=date_to)
    bought = PurchaseItem.objects.filter(purchase__branch__in=branches, purchase__is_opening=False,
                                         purchase__invoice_date__gte=date_from, purchase__invoice_date__lte=date_to)
    rows = defaultdict(lambda: {"sales": ZERO, "output": ZERO, "buy": ZERO, "input": ZERO})
    for r in lines.values("gst_rate").annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"), s=Sum("sgst_amount")):
        rows[r["gst_rate"]]["sales"] += r["t"]
        rows[r["gst_rate"]]["output"] += r["c"] + r["s"]
    for r in (credits.values("invoice_line__gst_rate")
              .annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"), s=Sum("sgst_amount"))):
        rows[r["invoice_line__gst_rate"]]["sales"] -= r["t"]
        rows[r["invoice_line__gst_rate"]]["output"] -= r["c"] + r["s"]
    for r in bought.values("gst_rate").annotate(t=Sum("taxable_amount"), g=Sum("gst_amount")):
        rows[r["gst_rate"]]["buy"] += r["t"]
        rows[r["gst_rate"]]["input"] += r["g"]
    out = [{"rate": f"{rate.normalize():f}%", "sales": r["sales"], "output": r["output"], "buy": r["buy"],
            "input": r["input"], "payable": r["output"] - r["input"]} for rate, r in sorted(rows.items())]
    columns = [col("rate", "GST rate"), col("sales", "Sales (taxable)", "money"), col("output", "GST on sales", "money"),
               col("buy", "Purchases (taxable)", "money"), col("input", "GST on purchases", "money"),
               col("payable", "GST to pay (+) / extra credit (-)", "money")]
    return {"columns": columns, "rows": out, "totals": _totals(out, columns, "rate") if out else None}


def fy_summary(branches, date_from, date_to, grouping=None):
    """One row per month inside the dates."""
    from apps.pharmacy.models import Purchase

    rows = defaultdict(lambda: {"bills": 0, "sales": ZERO, "gst": ZERO, "received": ZERO, "refunds": ZERO,
                                "buy": ZERO, "input": ZERO})
    invoices = Invoice.objects.filter(branch__in=branches, invoice_date__gte=date_from, invoice_date__lte=date_to)
    for r in (invoices.exclude(status="cancelled").annotate(p=TruncMonth("invoice_date")).values("p")
              .annotate(n=Count("id"))):
        rows[_period_key(r["p"], "month")]["bills"] += r["n"]
    for r in (invoices.annotate(p=TruncMonth("invoice_date")).values("p")
              .annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"), s=Sum("sgst_amount"), i=Sum("igst_amount"))):
        row = rows[_period_key(r["p"], "month")]
        row["sales"] += r["t"] or ZERO
        row["gst"] += (r["c"] or ZERO) + (r["s"] or ZERO) + (r["i"] or ZERO)
    notes = CreditNote.objects.filter(branch__in=branches, note_date__gte=date_from, note_date__lte=date_to)
    for r in (notes.annotate(p=TruncMonth("note_date")).values("p")
              .annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"), s=Sum("sgst_amount"))):
        row = rows[_period_key(r["p"], "month")]
        row["sales"] -= r["t"] or ZERO
        row["gst"] -= (r["c"] or ZERO) + (r["s"] or ZERO)
    for r in (notes.exclude(refund_mode="none").annotate(p=TruncMonth("note_date")).values("p")
              .annotate(s=Sum("refund_amount"))):
        rows[_period_key(r["p"], "month")]["refunds"] += r["s"]
    payments = Payment.objects.filter(branch__in=branches, paid_at__date__gte=date_from, paid_at__date__lte=date_to)
    for r in payments.annotate(p=TruncMonth("paid_at")).values("p").annotate(s=Sum("amount")):
        rows[_period_key(r["p"], "month")]["received"] += r["s"]
    purchases = Purchase.objects.filter(branch__in=branches, is_opening=False, invoice_date__gte=date_from,
                                        invoice_date__lte=date_to)
    for r in (purchases.annotate(p=TruncMonth("invoice_date")).values("p")
              .annotate(t=Sum("taxable_amount"), g=Sum("gst_amount"))):
        row = rows[_period_key(r["p"], "month")]
        row["buy"] += r["t"] or ZERO
        row["input"] += r["g"] or ZERO
    out = []
    for period in sorted(rows):
        r = rows[period]
        out.append({"period": period, "bills": r["bills"], "sales": r["sales"], "gst": r["gst"],
                    "received": r["received"] - r["refunds"], "buy": r["buy"], "input": r["input"],
                    "payable": r["gst"] - r["input"]})
    columns = [col("period", "Month", "month"), col("bills", "Bills", "int"),
               col("sales", "Sales (taxable, after returns)", "money"), col("gst", "GST on sales", "money"),
               col("received", "Money received (after refunds)", "money"), col("buy", "Purchases (taxable)", "money"),
               col("input", "GST on purchases", "money"), col("payable", "GST to pay (+) / extra credit (-)", "money")]
    return {"columns": columns, "rows": out, "totals": _totals(out, columns, "period") if out else None}


def sales_register(branches, date_from, date_to, grouping=None):
    """Every bill, then every credit note (shown in minus), oldest first. A cancelled bill is listed and its
    credit note takes the amount off."""
    rows = []
    invoices = (Invoice.objects.filter(branch__in=branches, invoice_date__gte=date_from, invoice_date__lte=date_to)
                .select_related("patient"))
    for inv in invoices:
        rows.append({"date": inv.invoice_date, "number": inv.number, "kind": "Bill", "party": _who(inv),
                     "taxable": inv.taxable_amount, "cgst": inv.cgst_amount, "sgst": inv.sgst_amount,
                     "round_off": inv.round_off, "total": inv.total_amount, "status": inv.get_status_display()})
    notes = (CreditNote.objects.filter(branch__in=branches, note_date__gte=date_from, note_date__lte=date_to)
             .select_related("invoice__patient"))
    for n in notes:
        rows.append({"date": n.note_date, "number": n.number, "kind": "Credit note", "party": _who(n.invoice),
                     "taxable": -n.taxable_amount, "cgst": -n.cgst_amount, "sgst": -n.sgst_amount,
                     "round_off": ZERO, "total": -n.total_amount, "status": f"Against {n.invoice.number}"})
    rows.sort(key=lambda r: (r["date"], r["number"]))
    columns = [col("date", "Date", "date"), col("number", "Number"), col("kind", "Type"), col("party", "Customer"),
               col("taxable", "Taxable value", "money"), col("cgst", "CGST", "money"), col("sgst", "SGST", "money"),
               col("round_off", "Round off", "money"), col("total", "Total", "money"), col("status", "Status")]
    totals = _totals(rows, columns, "date") if rows else None
    return {"columns": columns, "rows": rows, "totals": totals}


def purchase_register(branches, date_from, date_to, grouping=None):
    """Every supplier invoice entered in the dates (opening stock is not a purchase)."""
    from apps.pharmacy.models import Purchase

    purchases = (Purchase.objects.filter(branch__in=branches, is_opening=False, invoice_date__gte=date_from,
                                         invoice_date__lte=date_to)
                 .select_related("supplier").order_by("invoice_date", "created_at"))
    rows = [{"date": p.invoice_date, "supplier": p.supplier.name if p.supplier_id else "-",
             "gstin": (p.supplier.gstin if p.supplier_id else "") or "-", "invoice_no": p.invoice_no or "-",
             "taxable": p.taxable_amount, "discount": p.discount_amount, "gst": p.gst_amount,
             "other": p.other_charges + p.round_off, "total": p.total_amount} for p in purchases]
    columns = [col("date", "Date", "date"), col("supplier", "Supplier"), col("gstin", "Supplier GSTIN"),
               col("invoice_no", "Invoice no."), col("taxable", "Taxable value", "money"),
               col("discount", "Discount", "money"), col("gst", "GST", "money"),
               col("other", "Other charges / round off", "money"), col("total", "Total", "money")]
    return {"columns": columns, "rows": rows, "totals": _totals(rows, columns, "date") if rows else None}


def dues(branches, date_from, date_to, grouping=None):
    """Bills in the dates that are not fully paid (after credit notes and refunds). Phone numbers are masked."""
    today = timezone.localdate()
    invoices = (Invoice.objects.filter(branch__in=branches, invoice_date__gte=date_from, invoice_date__lte=date_to)
                .exclude(status="cancelled").select_related("patient").order_by("invoice_date", "number"))
    rows = [{"date": i.invoice_date, "number": i.number, "patient": _who(i),
             "phone": mask_phone(i.patient.mobile) if i.patient_id else "-",
             "total": i.total_amount - i.credited_amount, "paid": i.paid_amount - i.refunded_amount, "due": i.balance,
             "days": (today - i.invoice_date).days, "patient_id": str(i.patient_id) if i.patient_id else None}
            for i in invoices if i.balance > 0]
    columns = [col("date", "Date", "date"), col("number", "Bill no."), col("patient", "Patient"), col("phone", "Phone"),
               col("total", "Bill amount (after returns)", "money"), col("paid", "Paid", "money"),
               col("due", "Still due", "money"), col("days", "Days old", "int")]
    totals = _totals(rows, columns, "date") if rows else None
    if totals:
        totals["days"] = None
    return {"columns": columns, "rows": rows, "totals": totals}
