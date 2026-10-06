"""
Step 8 reports. Read-only: they only count what other modules saved (bills, payments, credit notes, visits).

Every report returns the same shape, so the screen, Excel and PDF can show any of them:
    {"columns": [{"key", "label", "type"}], "rows": [{...}], "totals": {...} or None}
Column types: text, date, month, int, money.

Reports:
- collection     money received per day or month: cash / UPI / card, refunds, net
- by_doctor      income per doctor: consultation, services & therapy, medicines, billed, received, due
- by_branch      the same per branch (for the owner)
- patients       patients seen per day or month: new cases vs follow-ups (repeat)
- follow_ups     missed follow-ups: follow-up date has passed and the patient has not come back
- gst            GST summary per HSN / SAC code and GST rate (bills minus credit notes). Check with your CA.

Money is counted the same way as the daily closing (billing.services.day_summary):
payments on the day they were received, refunds on the day of the credit note.
"""
from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal

from django.db.models import Count, Exists, F, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from apps.billing.models import CreditNote, CreditNoteLine, Invoice, InvoiceLine, Payment
from apps.common.utils import mask_phone
from apps.emr.models import Visit

ZERO = Decimal("0")
MODES = ("cash", "upi", "card")

# Which permission a user needs in a branch to see a report for that branch (on top of reports.view).
REPORTS = {
    "collection": {"title": "Collection by payment mode", "needs": "billing.view", "grouped": True},
    "by_doctor": {"title": "Income by doctor", "needs": "billing.view", "grouped": False},
    "by_branch": {"title": "Income by branch", "needs": "billing.view", "grouped": False},
    "patients": {"title": "New vs repeat patients", "needs": "appointments.view", "grouped": True},
    "follow_ups": {"title": "Missed follow-ups", "needs": "patients.view", "grouped": False},
    "gst": {"title": "GST summary", "needs": "billing.view", "grouped": False},
}


def col(key, label, kind="text"):
    return {"key": key, "label": label, "type": kind}


def _sum(qs, field):
    return qs.aggregate(s=Sum(field))["s"] or ZERO


def _period(grouping):
    """'day' -> one row per date; 'month' -> one row per month (key = first day of the month)."""
    return TruncMonth if grouping == "month" else TruncDate


def _period_key(value, grouping):
    if isinstance(value, datetime):  # months of payments come back as date-times
        value = timezone.localtime(value).date() if timezone.is_aware(value) else value.date()
    return value.replace(day=1) if grouping == "month" else value


def _totals(rows, columns, label_key):
    totals = {c["key"]: sum((r[c["key"]] for r in rows), ZERO if c["type"] == "money" else 0)
              for c in columns if c["type"] in ("money", "int")}
    totals[label_key] = "Total"
    return totals


# ---------------------------------------------------------------- collection

def collection(branches, date_from, date_to, grouping="day"):
    trunc = _period(grouping)
    payments = Payment.objects.filter(branch__in=branches, paid_at__date__gte=date_from, paid_at__date__lte=date_to)
    notes = CreditNote.objects.filter(branch__in=branches, note_date__gte=date_from, note_date__lte=date_to)
    invoices = Invoice.objects.filter(branch__in=branches, invoice_date__gte=date_from, invoice_date__lte=date_to)

    rows = defaultdict(lambda: {"bills": 0, **{m: ZERO for m in MODES}, "refunds": ZERO})
    for r in payments.annotate(p=trunc("paid_at")).values("p", "mode").annotate(s=Sum("amount")):
        rows[_period_key(r["p"], grouping)][r["mode"]] += r["s"]
    for r in (notes.exclude(refund_mode="none").annotate(p=trunc("note_date")).values("p")
              .annotate(s=Sum("refund_amount"))):
        rows[_period_key(r["p"], grouping)]["refunds"] += r["s"]
    for r in invoices.exclude(status="cancelled").annotate(p=trunc("invoice_date")).values("p").annotate(n=Count("id")):
        rows[_period_key(r["p"], grouping)]["bills"] += r["n"]

    out = []
    for period in sorted(rows):
        r = rows[period]
        received = sum((r[m] for m in MODES), ZERO)
        out.append({"period": period, "bills": r["bills"], **{m: r[m] for m in MODES},
                    "received": received, "refunds": r["refunds"], "net": received - r["refunds"]})
    columns = [col("period", "Month" if grouping == "month" else "Date", "month" if grouping == "month" else "date"),
               col("bills", "Bills", "int"), col("cash", "Cash", "money"), col("upi", "UPI", "money"),
               col("card", "Card", "money"), col("received", "Received", "money"),
               col("refunds", "Refunds", "money"), col("net", "Net collection", "money")]
    return {"columns": columns, "rows": out, "totals": _totals(out, columns, "period") if out else None}


# ---------------------------------------------------------------- income by doctor / branch

KIND_GROUPS = {"consultation": "consultation", "service": "services", "therapy": "services", "other": "services",
               "medicine": "medicines"}


def _income(branches, date_from, date_to, key):
    """Billed (after credit notes), received (after refunds) and still due, split by consultation / services /
    medicines, for bills made between the dates. key(path) gives the value to group by (doctor or branch);
    path leads from the row to its bill ("" for bills, "invoice__" for bill lines...)."""
    invoices = (Invoice.objects.filter(branch__in=branches, invoice_date__gte=date_from, invoice_date__lte=date_to)
                .annotate(who=key("")))
    lines = InvoiceLine.objects.filter(invoice__in=invoices).annotate(who=key("invoice__"))
    credits = CreditNoteLine.objects.filter(credit_note__invoice__in=invoices).annotate(who=key("credit_note__invoice__"))

    rows = defaultdict(lambda: {"bills": 0, "consultation": ZERO, "services": ZERO, "medicines": ZERO,
                                "billed": ZERO, "received": ZERO, "due": ZERO})
    for inv in invoices.values("who", "status", "total_amount", "credited_amount", "paid_amount", "refunded_amount"):
        r = rows[inv["who"]]
        if inv["status"] != "cancelled":
            r["bills"] += 1
        r["billed"] += inv["total_amount"] - inv["credited_amount"]
        r["received"] += inv["paid_amount"] - inv["refunded_amount"]
        r["due"] += max(ZERO, inv["total_amount"] - inv["credited_amount"] - (inv["paid_amount"] - inv["refunded_amount"]))
    for line in lines.values("who", "kind").annotate(s=Sum("total_amount")):
        rows[line["who"]][KIND_GROUPS.get(line["kind"], "services")] += line["s"]
    for line in credits.values("who", "invoice_line__kind").annotate(s=Sum("total_amount")):
        rows[line["who"]][KIND_GROUPS.get(line["invoice_line__kind"], "services")] -= line["s"]
    return rows


def by_doctor(branches, date_from, date_to, grouping=None):
    from apps.accounts.models import User

    # A pharmacy bill has no doctor of its own: use the doctor of the prescription it came from.
    rows = _income(branches, date_from, date_to,
                   lambda path: Coalesce(F(f"{path}doctor_id"), F(f"{path}prescription__doctor_id")))
    names = dict(User.objects.filter(id__in=[k for k in rows if k]).values_list("id", "full_name"))
    out = [{"name": names.get(k) or "No doctor (counter sale)", **v} for k, v in rows.items()]
    out.sort(key=lambda r: (r["name"] == "No doctor (counter sale)", -r["billed"]))
    return _income_table(out, "Doctor")


def by_branch(branches, date_from, date_to, grouping=None):
    rows = _income(branches, date_from, date_to, lambda path: F(f"{path}branch_id"))
    names = {b.id: b.name for b in branches}
    out = sorted(({"name": names.get(k, "?"), **v} for k, v in rows.items()), key=lambda r: -r["billed"])
    return _income_table(out, "Branch")


def _income_table(out, label):
    columns = [col("name", label), col("bills", "Bills", "int"), col("consultation", "Consultation", "money"),
               col("services", "Services & therapy", "money"), col("medicines", "Medicines", "money"),
               col("billed", "Billed (after returns)", "money"), col("received", "Received", "money"),
               col("due", "Still due", "money")]
    return {"columns": columns, "rows": out, "totals": _totals(out, columns, "name") if out else None}


# ---------------------------------------------------------------- new vs repeat patients

def patients(branches, date_from, date_to, grouping="day"):
    """A patient is a NEW case on the day of their first check-up with the clinic (any branch); later check-ups
    are follow-ups. Same rule as the dashboard."""
    trunc = _period(grouping)
    org_id = branches[0].organization_id if branches else None
    first_visit = (Visit.objects.filter(organization_id=org_id, patient_id=OuterRef("patient_id"))
                   .order_by("visit_date").values("visit_date")[:1])
    visits = (Visit.objects.filter(branch__in=branches, visit_date__gte=date_from, visit_date__lte=date_to)
              .annotate(p=trunc("visit_date"), first=Subquery(first_visit)))
    rows = defaultdict(lambda: {"visits": 0, "new": set(), "repeat": set(), "all": set()})
    for v in visits.values("p", "patient_id", "visit_date", "first"):
        r = rows[_period_key(v["p"], grouping)]
        r["visits"] += 1
        r["all"].add(v["patient_id"])
        (r["new"] if v["visit_date"] == v["first"] else r["repeat"]).add(v["patient_id"])
    out = []
    for period in sorted(rows):
        r = rows[period]
        new, repeat = len(r["new"]), len(r["repeat"] - r["new"])
        out.append({"period": period, "visits": r["visits"], "patients": len(r["all"]), "new": new, "repeat": repeat,
                    "repeat_percent": round(100 * repeat / len(r["all"])) if r["all"] else 0})
    columns = [col("period", "Month" if grouping == "month" else "Date", "month" if grouping == "month" else "date"),
               col("visits", "Check-ups", "int"), col("patients", "Patients", "int"), col("new", "New cases", "int"),
               col("repeat", "Follow-ups (repeat)", "int"), col("repeat_percent", "Repeat %", "int")]
    totals = None
    if out:
        everyone = {p for r in rows.values() for p in r["all"]}
        new_people = {p for r in rows.values() for p in r["new"]}
        totals = {"period": "Total", "visits": sum(r["visits"] for r in out), "patients": len(everyone),
                  "new": len(new_people), "repeat": len(everyone - new_people),
                  "repeat_percent": round(100 * len(everyone - new_people) / len(everyone)) if everyone else 0}
    return {"columns": columns, "rows": out, "totals": totals}


# ---------------------------------------------------------------- missed follow-ups

def follow_ups(branches, date_from, date_to, grouping=None):
    """Check-ups whose follow-up date (between the dates, and before today) has passed, and the patient has not
    had any check-up since (in any branch). Phone numbers are masked."""
    today = timezone.localdate()
    came_back = Visit.objects.filter(organization_id=OuterRef("organization_id"), patient_id=OuterRef("patient_id"),
                                     visit_date__gt=OuterRef("visit_date"))
    visits = (Visit.objects.filter(branch__in=branches, follow_up_date__gte=date_from,
                                   follow_up_date__lte=min(date_to, today - timedelta(days=1)))
              .exclude(Exists(came_back))
              .select_related("patient", "doctor", "branch").order_by("follow_up_date"))
    out = [{"patient": v.patient.full_name, "uhid": v.patient.uhid, "phone": mask_phone(v.patient.mobile),
            "doctor": v.doctor.full_name, "branch": v.branch.name, "last_visit": v.visit_date,
            "follow_up": v.follow_up_date, "days_late": (today - v.follow_up_date).days, "patient_id": str(v.patient_id)}
           for v in visits]
    columns = [col("patient", "Patient"), col("uhid", "UHID"), col("phone", "Phone"), col("doctor", "Doctor"),
               col("branch", "Branch"), col("last_visit", "Last check-up", "date"),
               col("follow_up", "Follow-up was due", "date"), col("days_late", "Days late", "int")]
    return {"columns": columns, "rows": out, "totals": None}


# ---------------------------------------------------------------- GST summary

def gst(branches, date_from, date_to, grouping=None):
    """Per HSN / SAC code and GST rate: taxable value and tax on bills, minus credit notes in the same dates.
    GST is CGST + SGST (same state). Confirm the figures with your CA before filing."""
    lines = InvoiceLine.objects.filter(invoice__branch__in=branches, invoice__invoice_date__gte=date_from,
                                       invoice__invoice_date__lte=date_to)
    credits = CreditNoteLine.objects.filter(credit_note__branch__in=branches, credit_note__note_date__gte=date_from,
                                            credit_note__note_date__lte=date_to)
    rows = defaultdict(lambda: {"taxable": ZERO, "cgst": ZERO, "sgst": ZERO, "credit_taxable": ZERO,
                                "credit_tax": ZERO})
    for r in (lines.values("hsn_code", "gst_rate")
              .annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"), s=Sum("sgst_amount"))):
        row = rows[(r["hsn_code"] or "", r["gst_rate"])]
        row["taxable"] += r["t"]
        row["cgst"] += r["c"]
        row["sgst"] += r["s"]
    for r in (credits.values("invoice_line__hsn_code", "invoice_line__gst_rate")
              .annotate(t=Sum("taxable_amount"), c=Sum("cgst_amount"), s=Sum("sgst_amount"))):
        row = rows[(r["invoice_line__hsn_code"] or "", r["invoice_line__gst_rate"])]
        row["credit_taxable"] += r["t"]
        row["credit_tax"] += r["c"] + r["s"]
    out = []
    for (code, rate), r in sorted(rows.items(), key=lambda kv: (kv[0][1], kv[0][0])):
        net_taxable = r["taxable"] - r["credit_taxable"]
        net_tax = r["cgst"] + r["sgst"] - r["credit_tax"]
        out.append({"code": code or "-", "rate": f"{rate.normalize():f}%", "taxable": r["taxable"], "cgst": r["cgst"],
                    "sgst": r["sgst"], "credit_taxable": r["credit_taxable"], "credit_tax": r["credit_tax"],
                    "net_taxable": net_taxable, "net_tax": net_tax})
    columns = [col("code", "HSN / SAC"), col("rate", "GST rate"), col("taxable", "Taxable value", "money"),
               col("cgst", "CGST", "money"), col("sgst", "SGST", "money"),
               col("credit_taxable", "Credit notes: taxable", "money"), col("credit_tax", "Credit notes: GST", "money"),
               col("net_taxable", "Net taxable", "money"), col("net_tax", "Net GST", "money")]
    totals = _totals(out, columns, "code") if out else None
    if totals:
        totals["rate"] = ""
    return {"columns": columns, "rows": out, "totals": totals}


BUILDERS = {"collection": collection, "by_doctor": by_doctor, "by_branch": by_branch, "patients": patients,
            "follow_ups": follow_ups, "gst": gst}


def build(code, branches, date_from, date_to, grouping="day"):
    return BUILDERS[code](list(branches), date_from, date_to, grouping)
