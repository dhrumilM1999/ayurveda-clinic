"""
Check-up rules: starting templates, checking exam answers, Prakriti scoring, starting and finishing a visit.
Other modules (prescriptions, billing...) should use these functions.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.appointments.services import change_status

from .models import ExamTemplate, Visit, VisitExam
from .templates_catalog import TEMPLATES

DOSHAS = ("vata", "pitta", "kapha")


# --- Templates --------------------------------------------------------------------
def ensure_exam_templates(organization) -> int:
    """Add the starting templates that are missing (never changes existing ones)."""
    existing = set(ExamTemplate.all_objects.filter(organization=organization).values_list("code", flat=True))
    added = 0
    for order, tpl in enumerate(TEMPLATES):
        if tpl["code"] in existing:
            continue
        ExamTemplate.objects.create(
            organization=organization, code=tpl["code"], version=tpl["version"], kind=tpl["kind"],
            name=tpl["name"]["en"], name_gu=tpl["name"]["gu"], name_hi=tpl["name"]["hi"],
            description=tpl.get("description", {}), fields=tpl["fields"], sort_order=order,
        )
        added += 1
    return added


def clean_exam_values(template: ExamTemplate, values) -> dict:
    """Keep only known fields with allowed answers. Gives a clear error for wrong input."""
    if not isinstance(values, dict):
        raise ValidationError({"values": "Answers must be a list of field: value."})
    cleaned = {}
    for field in template.fields:
        key = field["key"]
        value = values.get(key)
        if value in (None, "", []):
            continue
        allowed = {o["value"] for o in field.get("options", [])}
        kind = field["type"]
        if kind == "choice":
            if value not in allowed:
                raise ValidationError({key: "Please choose one of the given answers."})
        elif kind == "multi":
            if not isinstance(value, list) or not set(value) <= allowed:
                raise ValidationError({key: "Please choose from the given answers."})
            value = [o["value"] for o in field["options"] if o["value"] in value]  # keep the template's order
        elif kind == "number":
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValidationError({key: "Please enter a number."})
            if ("min" in field and value < field["min"]) or ("max" in field and value > field["max"]):
                raise ValidationError({key: f"Must be between {field.get('min')} and {field.get('max')}."})
            value = int(value) if value.is_integer() else value
        else:  # text
            value = str(value)[:2000]
        cleaned[key] = value
    return cleaned


def score_questionnaire(template: ExamTemplate, values: dict) -> dict:
    """
    Prakriti score: each answer counts for one dosha. Result in percent, plus the type:
    one dosha if it has 50% or more; two doshas if they are close; "sama" if all are about equal.
    """
    if template.kind != "questionnaire":
        return {}
    counts = {d: 0 for d in DOSHAS}
    for field in template.fields:
        answer = values.get(field["key"])
        if answer in counts:
            counts[answer] += 1
    answered = sum(counts.values())
    if not answered:
        return {"answered": 0, "total": len(template.fields)}
    percent = {d: round(counts[d] * 100 / answered) for d in DOSHAS}
    ranked = sorted(DOSHAS, key=lambda d: percent[d], reverse=True)
    top, second, third = ranked
    if percent[top] - percent[third] <= 10:
        prakriti_type = "sama"
    elif percent[top] >= 50 and percent[top] - percent[second] > 15:
        prakriti_type = top
    else:
        prakriti_type = "_".join(d for d in DOSHAS if d in (top, second))  # e.g. vata_pitta
    return {**percent, "type": prakriti_type, "answered": answered, "total": len(template.fields)}


def save_exam(visit: Visit, template: ExamTemplate, values, user) -> VisitExam:
    cleaned = clean_exam_values(template, values)
    exam = VisitExam.objects.filter(visit=visit, template=template).first()
    if exam is None:
        exam = VisitExam(organization_id=visit.organization_id, visit=visit, template=template, created_by=user)
    exam.template_code = template.code
    exam.template_version = template.version
    exam.values = cleaned
    exam.result = score_questionnaire(template, cleaned)
    exam.updated_by = user
    exam.save()
    return exam


def latest_prakriti(patient) -> dict | None:
    """The patient's most recent Prakriti result (from any branch), or None."""
    exam = (
        VisitExam.objects.filter(visit__patient=patient, template_code="prakriti")
        .select_related("visit").order_by("-visit__visit_date", "-updated_at").first()
    )
    if exam is None or not exam.result.get("answered"):
        return None
    return {**exam.result, "visit_date": str(exam.visit.visit_date)}


# --- Visits -------------------------------------------------------------------------
@transaction.atomic
def start_visit(*, patient, doctor, branch, user, appointment=None) -> tuple[Visit, bool]:
    """
    Open the check-up. With an appointment: reuse its visit if it already has one, and move the
    appointment to "With doctor". Returns (visit, created).
    """
    if appointment is not None:
        existing = Visit.objects.filter(appointment=appointment).first()
        if existing:
            return existing, False
        if appointment.date == timezone.localdate():
            if appointment.status == "booked":
                change_status(appointment, "check_in", user)
            if appointment.status == "checked_in":
                change_status(appointment, "start", user)
    visit = Visit.objects.create(
        organization_id=branch.organization_id, branch=branch, patient=patient, doctor=doctor,
        appointment=appointment, visit_date=timezone.localdate(), created_by=user, updated_by=user,
    )
    return visit, True


@transaction.atomic
def complete_visit(visit: Visit, user) -> Visit:
    visit.status = "completed"
    visit.completed_at = timezone.now()
    visit.updated_by = user
    visit.save(update_fields=["status", "completed_at", "updated_by", "updated_at"])
    appointment = visit.appointment
    if appointment and appointment.status in ("checked_in", "in_consultation"):
        change_status(appointment, "complete", user)
    return visit
