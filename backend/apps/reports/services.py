"""
Dashboard figures in plain OPD words. Read-only: this module only counts what other modules saved.
- OPD: booked, waiting, with doctor, seen, did not come; new cases vs follow-ups.
- Money (only for staff who may see bills): received today for OPD and pharmacy, still due.
"""
from decimal import Decimal

from django.db.models import Count, Q, Sum

from apps.appointments.models import Appointment
from apps.billing.models import Invoice, Payment
from apps.emr.models import Visit


def opd_counts(branch, day, doctor=None) -> dict:
    appointments = Appointment.objects.filter(branch=branch, date=day)
    visits = Visit.objects.filter(branch=branch, visit_date=day)
    if doctor is not None:
        appointments = appointments.filter(doctor=doctor)
        visits = visits.filter(doctor=doctor)
    by = dict(appointments.values_list("status").annotate(n=Count("id")).values_list("status", "n"))
    # New case = the patient's first check-up ever with this clinic; follow-up = seen before
    seen_before = Visit.objects.filter(organization_id=branch.organization_id, visit_date__lt=day)
    patients = set(visits.values_list("patient_id", flat=True))
    returning = set(seen_before.filter(patient_id__in=patients).values_list("patient_id", flat=True))
    return {
        "booked": sum(n for s, n in by.items() if s != "cancelled"),
        "waiting": by.get("checked_in", 0),
        "with_doctor": by.get("in_consultation", 0),
        "seen": by.get("completed", 0),
        "not_arrived": by.get("booked", 0),
        "no_show": by.get("no_show", 0),
        "cancelled": by.get("cancelled", 0),
        "walk_ins": appointments.filter(kind="walk_in").exclude(status="cancelled").count(),
        "new_cases": len(patients - returning),
        "follow_ups": len(patients & returning),
        "follow_ups_due": Visit.objects.filter(branch=branch, follow_up_date=day, **({"doctor": doctor} if doctor else {})).count(),
    }


def next_patients(branch, day, doctor, limit=5) -> list[dict]:
    rows = (Appointment.objects.filter(branch=branch, date=day, doctor=doctor, status__in=["checked_in", "in_consultation"])
            .select_related("patient").order_by("-status", "token_number", "checked_in_at")[:limit])
    return [{"appointment": str(a.id), "token_number": a.token_number, "patient": a.patient.full_name,
             "uhid": a.patient.uhid, "status": a.status, "reason": a.reason} for a in rows]


def money_today(branch, day) -> dict:
    payments = Payment.objects.filter(branch=branch, paid_at__date=day)
    received = {series: payments.filter(invoice__series=series).aggregate(s=Sum("amount"))["s"] or Decimal("0")
                for series in ("OP", "PH")}
    from apps.billing.models import CreditNote

    refunds = {series: CreditNote.objects.filter(branch=branch, note_date=day, invoice__series=series)
               .aggregate(s=Sum("refund_amount"))["s"] or Decimal("0") for series in ("OP", "PH")}
    open_bills = Invoice.objects.filter(branch=branch, status__in=["unpaid", "partly_paid"])
    due_today = sum((i.balance for i in open_bills.filter(invoice_date=day)), Decimal("0"))
    return {
        "opd": received["OP"] - refunds["OP"], "pharmacy": received["PH"] - refunds["PH"],
        "total": received["OP"] + received["PH"] - refunds["OP"] - refunds["PH"],
        "due_today": due_today, "unpaid_bills": open_bills.filter(invoice_date=day).count(),
        "bills_today": Invoice.objects.filter(branch=branch, invoice_date=day).filter(~Q(status="cancelled")).count(),
    }
