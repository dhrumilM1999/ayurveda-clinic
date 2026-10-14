"""
Pharmacy reports for a small clinic (one branch): what to buy, daily summary, top selling, slow items,
margin and GST of pharmacy bills. Every report returns {"columns", "rows", "totals"} so one screen can show all.
Money in these reports is in rupees; GST is CGST + SGST (same state). Check the GST figures with your CA.
"""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Sum
from django.utils import timezone

from apps.billing.models import CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment

from .models import DispenseItem, Purchase, StockBatch
from .services import rupees, stock_summary

ZERO = Decimal("0")
SLOW_DAYS = 90  # "not moving": nothing sold for this many days
REORDER_TARGET = 2  # buy enough to reach this many times the reorder level


def col(key, label, kind="text"):
    return {"key": key, "label": label, "kind": kind}


def _totals(rows, columns, first_key, label="Total"):
    """Sum of every money / number column."""
    totals = {c["key"]: sum((r[c["key"]] for r in rows), ZERO) for c in columns if c["kind"] in ("money", "number")}
    totals[first_key] = label
    return totals


def reorder(branch, date_from=None, date_to=None):
    """Medicines at or below their reorder level (usable stock), with a suggested quantity to buy."""
    rows = []
    for r in stock_summary(branch):
        level = r["reorder_level"]
        if level is None or r["usable"] > level:
            continue
        medicine = r["medicine"]
        last = (StockBatch.objects.filter(branch=branch, medicine=medicine).select_related("supplier")
                .order_by("-created_at").first())
        rows.append({
            "name": medicine.name, "usable": r["usable"], "level": level,
            "suggested": max(level * REORDER_TARGET - r["usable"], Decimal("1")),
            "supplier": last.supplier.name if last and last.supplier_id else "",
            "last_rate": last.purchase_rate if last and last.purchase_rate is not None else ZERO,
        })
    columns = [col("name", "Medicine"), col("usable", "In stock", "number"), col("level", "Reorder level", "number"),
               col("suggested", "Suggested to buy", "number"), col("supplier", "Last supplier"),
               col("last_rate", "Last buying price", "money")]
    return {"columns": columns, "rows": rows, "totals": None}


def daily(branch, date_from, date_to):
    """One row per day: pharmacy bills, returns, money received per payment mode, and purchases."""
    days = defaultdict(lambda: defaultdict(lambda: ZERO))
    for inv in Invoice.objects.filter(branch=branch, series="PH", invoice_date__range=(date_from, date_to)):
        d = days[inv.invoice_date]
        d["bills"] += 1
        d["gross"] += inv.gross_amount
        d["discount"] += inv.discount_amount
        d["billed"] += inv.total_amount
    for note in CreditNote.objects.filter(branch=branch, invoice__series="PH", note_date__range=(date_from, date_to)):
        days[note.note_date]["returns"] += note.total_amount
        if note.refund_mode in ("cash", "upi", "card"):
            days[note.note_date][note.refund_mode] -= note.refund_amount
    for p in Payment.objects.filter(branch=branch, invoice__series="PH", paid_at__date__range=(date_from, date_to)):
        days[timezone.localtime(p.paid_at).date()][p.mode] += p.amount
    for pu in Purchase.objects.filter(branch=branch, is_opening=False, invoice_date__range=(date_from, date_to)):
        days[pu.invoice_date]["purchases"] += pu.total_amount
    rows = []
    for day in sorted(days):
        d = days[day]
        rows.append({"date": str(day), "bills": d["bills"], "gross": d["gross"], "discount": d["discount"],
                     "billed": d["billed"], "returns": d["returns"], "net": d["billed"] - d["returns"],
                     "cash": d["cash"], "upi": d["upi"], "card": d["card"], "purchases": d["purchases"]})
    columns = [col("date", "Date"), col("bills", "Bills", "number"), col("gross", "Before discount", "money"),
               col("discount", "Discount", "money"), col("billed", "Billed", "money"),
               col("returns", "Returns (credit notes)", "money"), col("net", "Net sales", "money"),
               col("cash", "Cash received", "money"), col("upi", "UPI received", "money"),
               col("card", "Card received", "money"), col("purchases", "Purchases", "money")]
    return {"columns": columns, "rows": rows, "totals": _totals(rows, columns, "date") if rows else None}


def _sold(branch, date_from, date_to):
    """Per medicine: packs sold (minus packs brought back) and value, in the dates."""
    items = (DispenseItem.objects.filter(dispense__branch=branch, dispense__created_at__date__range=(date_from, date_to))
             .values("medicine_id", "medicine__name")
             .annotate(qty=Sum(F("quantity") - F("returned_quantity")), value=Sum("amount")))
    return {i["medicine_id"]: i for i in items}


def top_selling(branch, date_from, date_to):
    rows = [{"name": i["medicine__name"], "qty": i["qty"] or ZERO, "value": i["value"] or ZERO}
            for i in sorted(_sold(branch, date_from, date_to).values(), key=lambda i: -(i["value"] or ZERO))[:50]]
    columns = [col("name", "Medicine"), col("qty", "Packs sold", "number"), col("value", "Sales value", "money")]
    return {"columns": columns, "rows": rows, "totals": _totals(rows, columns, "name") if rows else None}


def non_moving(branch, date_from=None, date_to=None):
    """Medicines in stock that were not sold in the last SLOW_DAYS days (money tied up on the shelf)."""
    today = timezone.localdate()
    sold = _sold(branch, today - timedelta(days=SLOW_DAYS), today)
    rows = []
    for r in stock_summary(branch):
        if r["available"] <= 0 or r["medicine"].id in sold:
            continue
        cost = sum((b.quantity * (b.purchase_rate or ZERO) for b in
                    StockBatch.objects.filter(branch=branch, medicine=r["medicine"], quantity__gt=0)), ZERO)
        rows.append({"name": r["medicine"].name, "available": r["available"], "stock_value": rupees(cost)})
    rows.sort(key=lambda x: -x["stock_value"])
    columns = [col("name", "Medicine"), col("available", "In stock", "number"),
               col("stock_value", "Stock value (buying price)", "money")]
    return {"columns": columns, "rows": rows, "totals": _totals(rows, columns, "name") if rows else None}


def margin(branch, date_from, date_to):
    """Sale value (without GST) minus buying price. Lines whose batch has no buying price are left out."""
    items = (DispenseItem.objects.filter(dispense__branch=branch, dispense__created_at__date__range=(date_from, date_to),
                                         batch__purchase_rate__isnull=False)
             .select_related("medicine", "batch"))
    rows = defaultdict(lambda: {"qty": ZERO, "sales": ZERO, "cost": ZERO})
    for i in items:
        net_qty = i.quantity - i.returned_quantity
        if net_qty <= 0:
            continue
        r = rows[i.medicine.name]
        r["qty"] += net_qty
        r["sales"] += rupees(i.amount * (net_qty / i.quantity) * 100 / (100 + i.batch.gst_rate))
        r["cost"] += rupees(net_qty * i.batch.purchase_rate)
    out = [{"name": n, "qty": r["qty"], "sales": r["sales"], "cost": r["cost"], "margin": r["sales"] - r["cost"]}
           for n, r in sorted(rows.items(), key=lambda kv: -(kv[1]["sales"] - kv[1]["cost"]))]
    columns = [col("name", "Medicine"), col("qty", "Packs sold", "number"), col("sales", "Sales (without GST)", "money"),
               col("cost", "Buying price", "money"), col("margin", "Margin", "money")]
    return {"columns": columns, "rows": out, "totals": _totals(out, columns, "name") if out else None}


def gst(branch, date_from, date_to):
    """GST of pharmacy bills per HSN code and rate, minus credit notes in the same dates."""
    rows = defaultdict(lambda: {"taxable": ZERO, "tax": ZERO})
    lines = InvoiceLine.objects.filter(invoice__branch=branch, invoice__series="PH",
                                       invoice__invoice_date__range=(date_from, date_to))
    for r in lines.values("hsn_code", "gst_rate").annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"),
                                                           s=Sum("sgst_amount")):
        row = rows[(r["hsn_code"] or "-", r["gst_rate"])]
        row["taxable"] += r["t"]
        row["tax"] += r["c"] + r["s"]
    credits = CreditNoteLine.objects.filter(credit_note__branch=branch, credit_note__invoice__series="PH",
                                            credit_note__note_date__range=(date_from, date_to))
    for r in (credits.values("invoice_line__hsn_code", "invoice_line__gst_rate")
              .annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"), s=Sum("sgst_amount"))):
        row = rows[(r["invoice_line__hsn_code"] or "-", r["invoice_line__gst_rate"])]
        row["taxable"] -= r["t"]
        row["tax"] -= r["c"] + r["s"]
    out = [{"code": code, "rate": f"{rate.normalize():f}%", "taxable": r["taxable"], "tax": r["tax"],
            "cgst": rupees(r["tax"] / 2), "sgst": r["tax"] - rupees(r["tax"] / 2)}
           for (code, rate), r in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0]))]
    columns = [col("code", "HSN code"), col("rate", "GST rate"), col("taxable", "Taxable value (after returns)", "money"),
               col("cgst", "CGST", "money"), col("sgst", "SGST", "money"), col("tax", "Total GST", "money")]
    totals = _totals(out, columns, "code") if out else None
    if totals:
        totals["rate"] = ""
    return {"columns": columns, "rows": out, "totals": totals}


REPORTS = {
    "reorder": {"title": "What to buy (reorder list)", "build": reorder, "dates": False},
    "daily": {"title": "Daily pharmacy report", "build": daily, "dates": True},
    "top_selling": {"title": "Top selling medicines", "build": top_selling, "dates": True},
    "non_moving": {"title": "Slow / non-moving medicines", "build": non_moving, "dates": False},
    "margin": {"title": "Margin (profit) report", "build": margin, "dates": True},
    "gst": {"title": "GST of pharmacy bills", "build": gst, "dates": True},
}
