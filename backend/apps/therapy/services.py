"""
Therapy rules in one place (views call these; other modules should too):
- who may be booked (therapists), 
- a therapist or a room is never booked twice at the same time,
- creating the sessions of a plan,
- loading the starting list of therapies.
"""
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from rest_framework.exceptions import ValidationError

from apps.accounts.models import User

from .catalog import INSTRUCTIONS, THERAPIES
from .models import BUSY_STATUSES, TherapySession, TherapyType


def therapists_in_branch(branch):
    """Active staff whose role in this branch has "therapy.perform" (the Therapist role; give it to a doctor or
    admin role on the Roles screen if they do therapy too). Staff who only book sessions are not listed."""
    candidates = User.objects.filter(organization_id=branch.organization_id, is_active=True,
                                     branch_roles__branch=branch, branch_roles__is_deleted=False).distinct()
    return [u for u in candidates if _has_therapy_role(u, branch)]


def _has_therapy_role(user, branch) -> bool:
    from apps.accounts.models import UserBranchRole

    role = UserBranchRole.objects.filter(user=user, branch=branch, is_deleted=False, role__is_deleted=False).select_related("role").first()
    return bool(role and "therapy.perform" in role.role.permissions)


def _minutes(t) -> int:
    return t.hour * 60 + t.minute


def clashes(branch, date, start, end, therapist=None, room=None, exclude_id=None):
    """Sessions of the day that overlap the given time and use the same therapist or the same (full) room."""
    qs = TherapySession.objects.filter(branch=branch, date=date, status__in=BUSY_STATUSES,
                                       start_time__lt=end, end_time__gt=start)
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    found = []
    if therapist is not None:
        found += [("therapist", s) for s in qs.filter(therapist=therapist)]
    if room is not None:
        busy = list(qs.filter(room=room))
        if len(busy) >= max(room.capacity, 1):
            found += [("room", s) for s in busy[:1]]
    return found


def check_free(branch, date, start, end, therapist=None, room=None, exclude_id=None):
    """Raise a clear message when the therapist or the room is already busy."""
    if end <= start:
        raise ValidationError({"end_time": "The end time must be after the start time."})
    for what, s in clashes(branch, date, start, end, therapist, room, exclude_id):
        who = s.patient.full_name
        times = f"{s.start_time:%H:%M}-{s.end_time:%H:%M}"
        if what == "therapist":
            raise ValidationError({"therapist": f"{therapist.full_name} is already booked {times} ({who})."})
        raise ValidationError({"room": f"{room.name} is already in use {times} ({who})."})


def end_for(start, minutes: int):
    return (datetime.combine(datetime.today(), start) + timedelta(minutes=minutes)).time()


def load_sample_therapies(organization) -> int:
    """Add the starting list of therapies (skips names that already exist). Returns how many were added."""
    existing = set(TherapyType.objects.filter(organization=organization).values_list("name", flat=True))
    added = 0
    for order, (name, gu, hi, stage, minutes, material) in enumerate(THERAPIES):
        if name in existing:
            continue
        TherapyType.objects.create(organization=organization, name=name, name_gu=gu, name_hi=hi, stage=stage,
                                   duration_minutes=minutes, default_material=material, sort_order=order, is_sample=True,
                                   instructions=INSTRUCTIONS.get(name, ""))
        added += 1
    return added


def refresh_plan_status(plan):
    """A plan is Running once a session is done and Completed when every planned session is done."""
    if plan.status == "cancelled":
        return
    planned = sum(plan.items.values_list("sessions_planned", flat=True))
    done = plan.sessions.filter(status="done").count()
    started = plan.sessions.filter(status__in=["in_progress", "done"]).exists()
    new = "completed" if planned and done >= planned else ("active" if started else "planned")
    if new != plan.status:
        plan.status = new
        plan.save(update_fields=["status", "updated_at"])


def plan_print_data(plan, lang: str) -> dict:
    """Plain data for the printed therapy plan: therapies (in the patient's language), booked sessions."""

    def pick(t):
        return (getattr(t, f"name_{lang}", "") if lang in ("gu", "hi") else "") or t.name

    items = []
    for item in plan.items.select_related("therapy").all():
        items.append({"name": pick(item.therapy), "stage": item.stage, "sessions": item.sessions_planned,
                      "instructions": item.therapy.instructions, "notes": item.notes})
    sessions = [
        {"date": s.date, "start": s.start_time, "end": s.end_time, "therapy": pick(s.therapy),
         "therapist": s.therapist.full_name if s.therapist else "", "room": s.room.name if s.room else ""}
        for s in plan.sessions.exclude(status__in=["cancelled", "missed"]).select_related("therapy", "therapist", "room")
        .order_by("date", "start_time")
    ]
    return {"items": items, "sessions": sessions, "has_instructions": any(i["instructions"] for i in items)}


# --- Undo (a wrong click on a session) ----------------------------------------------------
UNDO_MINUTES = 60  # an undo is possible for this long after the last change


def undo_target(session):
    """The status a session would go back to (None = cannot be undone any more)."""
    if timezone.now() - session.updated_at > timedelta(minutes=UNDO_MINUTES):
        return None
    if session.status == "in_progress":
        return "scheduled"
    if session.status == "done":
        return "in_progress" if session.started_at else "scheduled"
    if session.status in ("missed", "cancelled"):
        if session.plan.status == "cancelled" or session.date < timezone.localdate():
            return None
        return "scheduled"
    return None


def undo_last_step(session, user) -> dict:
    """Go one step back. What the therapist already wrote (oil, quantity, response) is kept."""
    target = undo_target(session)
    if target is None:
        raise ValidationError({"detail": "This can no longer be undone."})
    old = session.status
    if target in ("scheduled", "in_progress"):
        check_free(session.branch, session.date, session.start_time, session.end_time, session.therapist, session.room,
                   exclude_id=session.pk)
    session.status = target
    session.updated_by = user
    fields = ["status", "updated_by", "updated_at"]
    if old == "done":
        session.completed_at = None
        fields.append("completed_at")
    if target == "scheduled" and session.started_at:
        session.started_at = None
        fields.append("started_at")
    session.save(update_fields=fields)
    refresh_plan_status(session.plan)
    return {"from": old, "to": target, "undo": True}


def bill_finished_session(session, user):
    """
    Additional setting "Bill each finished therapy session": put the therapy's price on the patient's OPD bill
    of the session day (one bill per patient per day; made if there is none yet). Does nothing when the switch is
    off, the therapy has no price, or this session is already on the bill (finish -> undo -> finish again).
    """
    from apps.billing.models import Invoice
    from apps.billing.opd import branch_services, charge_opd
    from apps.organizations.services import is_feature_enabled

    if not is_feature_enabled(session.branch, "therapy_auto_billing") or not is_feature_enabled(session.branch, "opd_billing"):
        return None
    service_id = session.therapy.service_id
    if not service_id:
        return None
    row = next((r for r in branch_services(session.branch) if r["service"].id == service_id), None)
    if row is None:  # the service is switched off in this branch
        return None
    earlier = Q(date__lt=session.date) | Q(date=session.date, start_time__lt=session.start_time)
    number = session.item.sessions.exclude(status="cancelled").filter(earlier).count() + 1
    description = f"{session.therapy.name} - session {number} of {session.item.sessions_planned} ({session.date:%d-%m-%Y})"
    bills = Invoice.objects.filter(branch=session.branch, series="OP", patient=session.patient, invoice_date=session.date)         .exclude(status="cancelled")
    if bills.filter(lines__description=description).exists():
        return None
    service = row["service"]
    line = {"kind": "service", "service": service, "description": description, "quantity": 1, "unit_price": row["price"],
            "discount_percent": 0, "gst_rate": service.gst_rate, "hsn_code": service.sac_code, "unit_label": ""}
    existing = bills.order_by("created_at").first()
    if existing is not None:
        from apps.billing.services import add_lines
        return add_lines(existing, user, [line])
    return charge_opd(session.branch, user, patient=session.patient, doctor=session.plan.doctor, lines=[line],
                      visit=session.plan.visit)


def session_reminder(session, name: str) -> dict:
    """
    A WhatsApp reminder for a therapy session (click-to-chat link; staff press Send), ONLY if the patient agreed to
    messages. `name` is the therapy name in the patient's language.
    """
    from apps.notifications.whatsapp import prepare_whatsapp
    from apps.patients.services import has_consent

    from .messages_catalog import REMINDER

    patient = session.patient
    if not has_consent(patient, "communication"):
        return {"consent": False, "sms_sent": False, "whatsapp_link": "", "message": ""}
    branch = session.branch
    text = (REMINDER.get(patient.preferred_language) or REMINDER["en"]).format(
        name=patient.first_name, therapy=name, clinic=branch.name, date=session.date.strftime("%d-%m-%Y"),
        time=session.start_time.strftime("%I:%M %p").lstrip("0"), phone=branch.phone or session.organization.phone or "")
    link = prepare_whatsapp(patient.mobile, text, organization=session.organization, purpose="therapy_reminder")
    return {"consent": True, "sms_sent": False, "whatsapp_link": link, "message": text}
