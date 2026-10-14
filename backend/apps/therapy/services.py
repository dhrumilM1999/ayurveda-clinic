"""
Therapy rules in one place (views call these; other modules should too):
- who may be booked (therapists), 
- a therapist or a room is never booked twice at the same time,
- creating the sessions of a plan,
- loading the starting list of therapies.
"""
from datetime import datetime, timedelta

from django.db.models import Q
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User

from .catalog import INSTRUCTIONS, THERAPIES
from .models import BUSY_STATUSES, TherapySession, TherapyType


def therapists_in_branch(branch):
    """Active staff of the branch whose role may record therapy (therapists, doctors, admins)."""
    candidates = User.objects.filter(organization_id=branch.organization_id, is_active=True).filter(
        Q(is_org_admin=True) | Q(branch_roles__branch=branch, branch_roles__is_deleted=False)).distinct()
    return [u for u in candidates if u.is_org_admin or _has_therapy_role(u, branch)]


def _has_therapy_role(user, branch) -> bool:
    from apps.accounts.services import branch_permissions

    return "therapy.manage" in branch_permissions(user, branch)


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
