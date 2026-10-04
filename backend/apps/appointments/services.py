"""
Appointment rules: time slots, token numbers, status changes and patient messages.
Other modules (billing, EMR...) should call these functions instead of changing appointments directly.
"""
from datetime import date as date_cls
from datetime import datetime, time, timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.accounts.models import DoctorSchedule
from apps.notifications.sms import send_sms
from apps.notifications.whatsapp import prepare_whatsapp
from apps.patients.services import has_consent

from .messages_catalog import MESSAGES
from .models import ACTIVE_STATUSES, Appointment, TokenSequence


# --- Time slots -------------------------------------------------------------------
def _add_minutes(t: time, minutes: int) -> time:
    return (datetime.combine(date_cls.min, t) + timedelta(minutes=minutes)).time()


def doctor_slots(branch, doctor, day) -> list[dict]:
    """
    All time slots of a doctor in a branch on one day, from the doctor's schedule.
    Each slot: {"start": "10:00", "end": "10:15", "status": "free" | "booked" | "past"}.
    A slot booked at ANY branch counts as booked (a doctor can't be in two places).
    """
    schedules = DoctorSchedule.objects.filter(
        branch=branch, doctor=doctor, weekday=day.weekday(), is_active=True,
    ).order_by("start_time")
    taken = set(
        Appointment.objects.filter(doctor=doctor, date=day, start_time__isnull=False)
        .exclude(status="cancelled").values_list("start_time", flat=True)
    )
    now = timezone.localtime()
    slots = []
    for schedule in schedules:
        start = schedule.start_time
        while True:
            end = _add_minutes(start, schedule.slot_minutes)
            if end > schedule.end_time or end <= start:
                break
            if start in taken:
                status = "booked"
            elif day < now.date() or (day == now.date() and start <= now.time()):
                status = "past"
            else:
                status = "free"
            slots.append({"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M"), "status": status})
            start = end
    return slots


def slot_end(branch, doctor, day, start: time) -> time:
    """The end time of a free slot, or a clear error if the slot can't be booked."""
    wanted = start.strftime("%H:%M")
    for slot in doctor_slots(branch, doctor, day):
        if slot["start"] == wanted:
            if slot["status"] == "booked":
                raise ValidationError({"start_time": "This time is already booked. Please pick another time."})
            if slot["status"] == "past":
                raise ValidationError({"start_time": "This time has already passed."})
            return datetime.strptime(slot["end"], "%H:%M").time()
    raise ValidationError({"start_time": "The doctor does not sit at this time in this branch."})


# --- Tokens -----------------------------------------------------------------------
def next_token(branch, doctor, day) -> int:
    """Next token number for a doctor in a branch on a day. Safe when two people click at once."""
    with transaction.atomic():
        TokenSequence.objects.get_or_create(branch=branch, doctor=doctor, date=day)
        seq = TokenSequence.objects.select_for_update().get(branch=branch, doctor=doctor, date=day)
        seq.last_number += 1
        seq.save(update_fields=["last_number"])
        return seq.last_number


# --- Status changes ---------------------------------------------------------------
# action: (allowed current statuses, new status, timestamp field)
TRANSITIONS = {
    "check_in": ({"booked"}, "checked_in", "checked_in_at"),
    "start": ({"checked_in"}, "in_consultation", "consultation_started_at"),
    "complete": ({"checked_in", "in_consultation"}, "completed", "completed_at"),
    "no_show": ({"booked"}, "no_show", None),
    "cancel": ({"booked", "checked_in"}, "cancelled", "cancelled_at"),
}

TODAY_ONLY = {"check_in", "start", "complete"}


def change_status(appointment: Appointment, action: str, user, cancel_reason: str = "") -> dict:
    """Move an appointment to its next status. Returns {"from": old, "to": new} for the audit log."""
    allowed, new_status, stamp = TRANSITIONS[action]
    if appointment.status not in allowed:
        raise ValidationError({"detail": f"Not possible: the appointment is '{appointment.get_status_display()}'."})
    if action in TODAY_ONLY and appointment.date != timezone.localdate():
        raise ValidationError({"detail": "This can only be done on the day of the appointment."})
    old_status = appointment.status
    fields = ["status", "updated_by", "updated_at"]
    appointment.status = new_status
    appointment.updated_by = user
    if stamp:
        setattr(appointment, stamp, timezone.now())
        fields.append(stamp)
    if action == "check_in" and appointment.token_number is None:
        appointment.token_number = next_token(appointment.branch, appointment.doctor, appointment.date)
        fields.append("token_number")
    if action == "cancel":
        appointment.cancel_reason = cancel_reason[:200]
        fields.append("cancel_reason")
    appointment.save(update_fields=fields)
    return {"from": old_status, "to": new_status}


def patient_has_active_appointment(patient, doctor, day, exclude_id=None) -> bool:
    qs = Appointment.objects.filter(patient=patient, doctor=doctor, date=day, status__in=ACTIVE_STATUSES)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()


# --- Messages to the patient -------------------------------------------------------
def appointment_message(appointment: Appointment, event: str) -> str:
    patient = appointment.patient
    texts = MESSAGES[event]
    template = texts.get(patient.preferred_language) or texts["en"]
    branch = appointment.branch
    return template.format(
        name=patient.first_name,
        doctor=appointment.doctor.full_name,
        clinic=branch.name,
        date=appointment.date.strftime("%d-%m-%Y"),
        time=appointment.start_time.strftime("%I:%M %p").lstrip("0") if appointment.start_time else "",
        token=appointment.token_number or "",
        phone=branch.phone or appointment.organization.phone or "",
    )


def event_for(appointment: Appointment) -> str:
    """Which message fits the appointment right now."""
    if appointment.status == "cancelled":
        return "cancelled"
    if appointment.token_number and appointment.status in ("checked_in", "in_consultation"):
        return "token"
    return "rescheduled" if appointment.reschedule_count else "booked"


def notify_patient(appointment: Appointment, event: str, send_sms_now: bool = True) -> dict:
    """
    Tell the patient about the appointment, ONLY if they gave consent for SMS/WhatsApp messages.
    SMS goes through the SMS adapter; for WhatsApp we return a click-to-chat link for staff.
    """
    patient = appointment.patient
    if not has_consent(patient, "communication"):
        return {"consent": False, "sms_sent": False, "whatsapp_link": "", "message": ""}
    text = appointment_message(appointment, event)
    purpose = f"appointment_{event}"
    if send_sms_now:
        send_sms(patient.mobile, text, organization=appointment.organization, purpose=purpose)
    link = prepare_whatsapp(patient.mobile, text, organization=appointment.organization, purpose=purpose)
    return {"consent": True, "sms_sent": send_sms_now, "whatsapp_link": link, "message": text}
