"""
Check-up rules: starting templates, checking exam answers, Prakriti scoring, starting and finishing a visit.
Other modules (prescriptions, billing...) should use these functions.
"""
import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.appointments.services import change_status

from .models import ExamTemplate, ExamTemplateVersion, Visit, VisitExam
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
        template = ExamTemplate.objects.create(
            organization=organization, code=tpl["code"], version=tpl["version"], kind=tpl["kind"],
            name=tpl["name"]["en"], name_gu=tpl["name"]["gu"], name_hi=tpl["name"]["hi"],
            description=tpl.get("description", {}), fields=tpl["fields"], sort_order=order,
        )
        ExamTemplateVersion.objects.create(template=template, version=template.version, fields=template.fields)
        added += 1
    return added


# --- Editing templates (admin screen) -------------------------------------------------
FIELD_TYPES = {"choice", "multi", "number", "text"}
KEY_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
MAX_FIELDS = 60
MAX_OPTIONS = 30


def _label(raw, where) -> dict:
    if not isinstance(raw, dict) or not str(raw.get("en", "")).strip():
        raise ValidationError({"fields": f"{where}: the English text is missing."})
    return {lang: str(raw.get(lang, "")).strip()[:200] for lang in ("en", "gu", "hi")}


def validate_template_fields(kind: str, fields) -> list:
    """Check the questions of a template made on the admin screen, and return a clean copy."""
    if not isinstance(fields, list) or not fields:
        raise ValidationError({"fields": "Add at least one question."})
    if len(fields) > MAX_FIELDS:
        raise ValidationError({"fields": f"At most {MAX_FIELDS} questions."})
    cleaned, keys = [], set()
    for number, field in enumerate(fields, start=1):
        where = f"Question {number}"
        if not isinstance(field, dict):
            raise ValidationError({"fields": f"{where} is not valid."})
        key = str(field.get("key", "")).strip()
        if not KEY_RE.match(key) or key in keys:
            raise ValidationError({"fields": f"{where}: short name must be unique, lowercase letters/numbers/_ ."})
        keys.add(key)
        ftype = field.get("type")
        if kind == "questionnaire":
            ftype = "choice"  # every Prakriti-type question has one answer that counts for a dosha
        if ftype not in FIELD_TYPES:
            raise ValidationError({"fields": f"{where}: unknown answer type."})
        item = {"key": key, "type": ftype, "label": _label(field.get("label"), where)}
        if ftype in ("choice", "multi"):
            options = field.get("options") or []
            if not isinstance(options, list) or not 1 <= len(options) <= MAX_OPTIONS:
                raise ValidationError({"fields": f"{where}: add 1 to {MAX_OPTIONS} answers."})
            values, clean_options = set(), []
            for opt in options:
                value = str((opt or {}).get("value", "")).strip()
                if kind == "questionnaire":
                    if value not in DOSHAS:
                        raise ValidationError({"fields": f"{where}: each answer must count for Vata, Pitta or Kapha."})
                elif not KEY_RE.match(value) or value in values:
                    raise ValidationError({"fields": f"{where}: answer short names must be unique."})
                values.add(value)
                clean_options.append({"value": value, "label": _label(opt.get("label"), where)})
            item["options"] = clean_options
        if ftype == "number":
            item["unit"] = str(field.get("unit") or "")[:20]
            for limit in ("min", "max"):
                if field.get(limit) not in (None, ""):
                    try:
                        item[limit] = float(field[limit])
                    except (TypeError, ValueError):
                        raise ValidationError({"fields": f"{where}: {limit} must be a number."})
        cleaned.append(item)
    return cleaned


def save_template(template: ExamTemplate, data: dict, user) -> ExamTemplate:
    """Update a template. If the questions change, the version goes up and the old questions are kept."""
    for name in ("name", "name_gu", "name_hi"):
        if name in data:
            setattr(template, name, str(data[name] or "").strip()[:150])
    if not template.name:
        raise ValidationError({"name": "Please give the template a name."})
    if "description" in data and isinstance(data["description"], dict):
        template.description = {k: str(data["description"].get(k, ""))[:500] for k in ("en", "gu", "hi")}
    for name in ("is_active", "sort_order"):
        if name in data:
            setattr(template, name, data[name])
    with transaction.atomic():
        if "fields" in data:
            fields = validate_template_fields(template.kind, data["fields"])
            if fields != template.fields:
                template.version += 1
                template.fields = fields
                ExamTemplateVersion.objects.create(template=template, version=template.version, fields=fields,
                                                   created_by=user)
        template.updated_by = user
        template.save()
    return template


def create_template(organization, data: dict, user) -> ExamTemplate:
    kind = data.get("kind") if data.get("kind") in ("form", "questionnaire") else "form"
    name = str(data.get("name") or "").strip()
    if not name:
        raise ValidationError({"name": "Please give the template a name."})
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40] or "template"
    code, n = base, 2
    while ExamTemplate.all_objects.filter(organization=organization, code=code).exists():
        code, n = f"{base}_{n}", n + 1
    fields = validate_template_fields(kind, data.get("fields"))
    with transaction.atomic():
        template = ExamTemplate.objects.create(
            organization=organization, code=code, kind=kind, version=1, name=name[:150],
            name_gu=str(data.get("name_gu") or "")[:150], name_hi=str(data.get("name_hi") or "")[:150],
            fields=fields, sort_order=ExamTemplate.objects.filter(organization=organization).count(),
            created_by=user, updated_by=user,
        )
        ExamTemplateVersion.objects.create(template=template, version=1, fields=fields, created_by=user)
    return template


def fields_for_version(template: ExamTemplate, version: int) -> list:
    """The questions as they were in that version (falls back to the current ones)."""
    if version == template.version:
        return template.fields
    snapshot = ExamTemplateVersion.objects.filter(template=template, version=version).first()
    return snapshot.fields if snapshot else template.fields


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
        if appointment.date > timezone.localdate():
            raise ValidationError({"detail": "This appointment is on a later date. The check-up opens on that day."})
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
    from apps.prescriptions.services import finalize_for_visit  # here, to avoid a circular import

    finalize_for_visit(visit, user)
    return visit


def last_visit_date(patient, doctor, before):
    """Date of the patient's latest check-up with this doctor before a day (any branch), or None.
    Used by billing to tell a new case from a follow-up."""
    return (Visit.objects.filter(patient=patient, doctor=doctor, visit_date__lt=before)
            .order_by("-visit_date").values_list("visit_date", flat=True).first())
