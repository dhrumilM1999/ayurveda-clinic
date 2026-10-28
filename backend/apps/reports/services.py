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
        "waiting": by.get("checked_in", 0) + by.get("in_consultation", 0),  # no separate "With doctor" status
        "with_doctor": 0,
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
            .select_related("patient").order_by("token_number", "checked_in_at")[:limit])
    return [{"appointment": str(a.id), "token_number": a.token_number, "patient": a.patient.full_name,
             "uhid": a.patient.uhid, "status": "checked_in", "reason": a.reason} for a in rows]


def attention(branch, day, now_time, with_bills=False, with_therapy=False) -> dict:
    """What the front desk should look at now: the next appointments, patients who did not come on time,
    patients seen but not billed, and therapy sessions that were not done on time."""
    today = Appointment.objects.filter(branch=branch, date=day).select_related("patient", "doctor")
    booked = today.filter(status="booked").exclude(start_time__isnull=True)
    late = booked.filter(start_time__lt=now_time).order_by("start_time")
    upcoming = booked.filter(start_time__gte=now_time).order_by("start_time")[:5]

    def row(a):
        return {"appointment": str(a.id), "time": a.start_time.strftime("%H:%M"), "patient": a.patient.full_name,
                "uhid": a.patient.uhid, "doctor": a.doctor.full_name, "reason": a.reason}

    data = {"upcoming": [row(a) for a in upcoming], "time_passed": late.count(), "time_passed_list": [row(a) for a in late[:5]]}
    if with_bills:
        seen = today.filter(status__in=["checked_in", "in_consultation", "completed"])
        billed = Invoice.objects.filter(branch=branch, series="OP").exclude(status="cancelled").filter(
            Q(appointment__in=seen) | Q(visit__appointment__in=seen))
        billed_ids = set(billed.values_list("appointment_id", flat=True)) | set(billed.values_list("visit__appointment_id", flat=True))
        data["to_bill"] = seen.exclude(id__in=billed_ids).count()
    if with_therapy:
        from apps.therapy.models import TherapySession

        sessions = TherapySession.objects.filter(branch=branch, date=day)
        data["therapy_overdue"] = (sessions.filter(status="scheduled", end_time__lt=now_time).count()
                                   + sessions.filter(status="missed").count())
    return data


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
