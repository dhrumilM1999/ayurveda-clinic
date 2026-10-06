"""
Making the print-outs: letterhead, document number, QR "is this genuine?" link, DUPLICATE COPY, and the
content of each document in the patient's language. The look is in templates/documents/*.html (SAFE TO EDIT).
"""
import base64
import mimetypes

from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.common.services import translated_master

from .models import IssuedDocument
from .words import PRAKRITI_GUIDANCE, words_for

SIZES = {  # width, height, margin
    "a4": ("210mm", "297mm", "12mm"),
    "a5": ("148mm", "210mm", "8mm"),
    "a6": ("105mm", "148mm", "6mm"),
}
DURATION_WORDS = {
    "days": {"en": "days", "gu": "દિવસ", "hi": "दिन"},
    "weeks": {"en": "weeks", "gu": "અઠવાડિયા", "hi": "हफ़्ते"},
    "months": {"en": "months", "gu": "મહિના", "hi": "महीने"},
}


def language_of(patient, asked: str | None = None) -> str:
    lang = asked or getattr(patient, "preferred_language", "en")
    return lang if lang in ("en", "gu", "hi") else "en"


def _data_uri(field_file) -> str:
    """An uploaded image (logo, signature) as a data: link the PDF can show; '' if missing."""
    if not field_file:
        return ""
    try:
        with field_file.open("rb") as handle:
            content = handle.read()
    except (OSError, ValueError):
        return ""
    mime = mimetypes.guess_type(field_file.name)[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(content).decode()}"


def _qr(text: str) -> str:
    import segno

    return segno.make(text, error="m").svg_data_uri(scale=3, border=1)


@transaction.atomic
def issue(kind: str, object_id, *, branch, patient=None, doctor=None, issued_on=None, series="", number="") -> IssuedDocument:
    """The record of this document (made the first time it is printed). series: numbering, e.g. "RX"."""
    doc = IssuedDocument.objects.select_for_update().filter(kind=kind, object_id=str(object_id)).first()
    if doc is None:
        day = issued_on or timezone.localdate()
        if series and not number:
            from apps.billing.services import next_number

            number, _ = next_number(branch, series, day)
        doc = IssuedDocument.objects.create(
            organization_id=branch.organization_id, branch=branch, kind=kind, object_id=str(object_id),
            number=number, patient=patient, doctor=doctor, issued_on=day,
        )
    return doc


def mark_printed(doc: IssuedDocument) -> bool:
    """Count a real print. Returns True if this is a reprint (DUPLICATE COPY)."""
    duplicate = doc.print_count > 0
    IssuedDocument.objects.filter(pk=doc.pk).update(print_count=doc.print_count + 1, last_printed_at=timezone.now())
    return duplicate


def verify_url(doc: IssuedDocument) -> str:
    return f"{settings.PUBLIC_APP_URL}/verify/{doc.token}"


def pad_for(branch, size: str):
    """
    Pre-printed pad (Settings -> Branch details): the clinic's own paper already has the letterhead, so the
    print-out leaves blank space at the top / bottom and prints no letterhead. A4 and A5 only.
    """
    if not branch.print_on_pad or size not in ("a4", "a5"):
        return None
    return {"top": f"{branch.pad_top_mm}mm", "bottom": f"{branch.pad_bottom_mm}mm"}


def letterhead(branch, doctor) -> dict:
    org = branch.organization
    return {
        "organization": org, "branch": branch, "logo": _data_uri(org.logo) if org.logo_on_documents else "",
        "address": ", ".join(filter(None, [branch.address, branch.city, branch.pincode])),
        "doctor": {
            "name": doctor.full_name, "qualification": doctor.qualification,
            "registration_number": doctor.registration_number, "signature": _data_uri(doctor.signature),
        } if doctor else None,
    }


def render(template: str, size: str, context: dict) -> bytes:
    from weasyprint import HTML

    width, height, margin = SIZES.get(size, SIZES["a4"])
    html = render_to_string(f"documents/{template}", {
        **context, "size": size, "page_width": width, "page_height": height, "page_margin": margin,
    })
    return HTML(string=html).write_pdf()


def _patient(patient, w) -> dict:
    return {"name": patient.full_name, "uhid": patient.uhid, "age": patient.age_years,
            "gender": w.get(patient.gender, "")}


def _vitals(patient, day):
    vital = patient.vitals.filter(recorded_at__date=day).order_by("-recorded_at").first()
    if vital is None:
        return None
    return {
        "bp": f"{vital.bp_systolic}/{vital.bp_diastolic}" if vital.bp_systolic and vital.bp_diastolic else "",
        "pulse": vital.pulse or "", "weight": vital.weight_kg or "", "temperature": vital.temperature_f or "",
    }


def _times(frequency: str):
    parts = [p.strip() for p in (frequency or "").split("-")]
    return parts if len(parts) == 3 and all(parts) else None


# --- Each document --------------------------------------------------------------------------------
def prescription_context(prescription, lang: str) -> dict:
    visit, patient = prescription.visit, prescription.patient
    org_id = prescription.organization_id
    w = words_for(lang)
    items = []
    for item in prescription.items.select_related("medicine"):
        duration, unit = (item.duration, item.duration_unit) if item.duration else (prescription.medicine_days, "days")
        items.append({
            "name": item.medicine_name, "form": item.dosage_form,
            "strength": item.medicine.strength if item.medicine_id else "",
            "dose": f"{item.dose} {translated_master(org_id, 'dose_unit', item.dose_unit, lang)}".strip(),
            "frequency": item.frequency, "times": _times(item.frequency),
            "timing": translated_master(org_id, "medicine_timing", item.timing, lang),
            "anupana": translated_master(org_id, "anupana", item.anupana, lang),
            # e.g. "with warm water" / "હૂંફાળું પાણી સાથે" (word order follows the language)
            "with_anupana": w["with_x"].format(x=translated_master(org_id, "anupana", item.anupana, lang)) if item.anupana else "",
            "duration": f"{duration} {DURATION_WORDS.get(unit, DURATION_WORDS['days'])[lang]}" if duration else "",
            "quantity": item.quantity, "instructions": item.instructions,
        })
    return {
        "w": w, "lang": lang, "patient": _patient(patient, w), "date": visit.visit_date,
        "token": visit.appointment.token_number if visit.appointment_id else None,
        "vitals": _vitals(patient, visit.visit_date),
        "complaints": [c.get("label", "") for c in (visit.complaints or []) if c.get("label")],
        "diagnoses": [d.get("label", "") for d in (visit.diagnoses or []) if d.get("label")],
        "items": items, "notes": prescription.notes,
        "advice": [translated_master(org_id, "advice", a, lang) for a in (visit.advice or [])],
        "advice_notes": visit.advice_notes,
        "follow_up_date": visit.follow_up_date, "follow_up_notes": visit.follow_up_notes,
        **letterhead(prescription.branch, prescription.doctor),
    }


def _in(label, lang: str) -> str:
    """A {"en", "gu", "hi"} label in the language (English when that language is empty)."""
    if isinstance(label, dict):
        return label.get(lang) or label.get("en", "")
    return str(label or "")


def _exam_rows(exam, lang: str) -> list[tuple[str, str]]:
    """The answers of one filled examination form as (question, answer) in the language, in the form's order."""
    from apps.emr.services import fields_for_version

    values = exam.values or {}
    rows = []
    for field in fields_for_version(exam.template, exam.template_version):
        value = values.get(field["key"])
        if value in (None, "", []):
            continue
        options = {o["value"]: _in(o["label"], lang) for o in field.get("options", [])}
        if field["type"] == "choice":
            text = options.get(value, str(value))
        elif field["type"] == "multi":
            text = ", ".join(options.get(v, str(v)) for v in value)
        elif field["type"] == "number":
            text = f"{value} {field.get('unit', '')}".strip()
        else:
            text = str(value)
        rows.append((_in(field["label"], lang), text))
    return rows


def _condition(item, lang: str, w: dict) -> str:
    """A known condition, e.g. "Diabetes (since 2019)", in the language when a translation exists."""
    master = item.condition
    name = (getattr(master, f"label_{lang}", "") if lang != "en" else "") or master.label
    return f"{name} ({w['since_x'].format(x=item.since)})" if item.since else name


def detailed_context(prescription, lang: str) -> dict:
    """
    Extra parts of the DETAILED prescription: the full check-up (history, examination forms, Prakriti result,
    complaints with duration, diagnoses with codes, all vitals) and the patient's known conditions, allergies and
    other medicines. Only what was filled in is printed.
    """
    visit, patient = prescription.visit, prescription.patient
    w = words_for(lang)
    vital = patient.vitals.filter(recorded_at__date=visit.visit_date).order_by("-recorded_at").first()
    vitals_full = []
    if vital is not None:
        if vital.bp_systolic and vital.bp_diastolic:
            vitals_full.append((w["bp"], f"{vital.bp_systolic}/{vital.bp_diastolic} mmHg"))
        for label, value, unit in ((w["pulse"], vital.pulse, "/min"), (w["temperature"], vital.temperature_f, "°F"),
                                   (w["spo2"], vital.spo2, "%"), (w["resp_rate"], vital.respiratory_rate, "/min"),
                                   (w["weight"], vital.weight_kg, "kg"), (w["height"], vital.height_cm, "cm"),
                                   (w["bmi"], vital.bmi, "")):
            if value:
                vitals_full.append((label, f"{value} {unit}".strip()))
    complaints = []
    for c in visit.complaints or []:
        if not c.get("label"):
            continue
        extra = []
        if c.get("duration"):
            extra.append(f"{w['duration']} {c['duration']} {DURATION_WORDS.get(c.get('duration_unit') or 'days', DURATION_WORDS['days'])[lang]}")
        if c.get("severity"):
            extra.append(str(c["severity"]))
        if c.get("notes"):
            extra.append(c["notes"])
        complaints.append({"label": c["label"], "extra": ", ".join(extra)})
    diagnoses = [{"label": d["label"], "code": d.get("code", ""), "kind": w.get(d.get("kind", ""), "")}
                 for d in visit.diagnoses or [] if d.get("label")]
    exams, prakriti = [], None
    for exam in visit.exams.select_related("template").order_by("created_at"):
        name = (getattr(exam.template, f"name_{lang}", "") if lang != "en" else "") or exam.template.name
        if exam.template.kind == "questionnaire":
            result = exam.result or {}
            if result.get("answered"):
                kind = result.get("type", "")
                prakriti = {
                    "type": " - ".join(w.get(p, p) for p in kind.split("_")) if kind and kind != "sama" else w["sama"],
                    "bars": [(w[d], result.get(d, 0)) for d in ("vata", "pitta", "kapha")],
                }
            continue
        rows = _exam_rows(exam, lang)
        if rows:
            # Two answers side by side, so a full examination fits on less paper
            exams.append({"name": name, "rows": rows, "pairs": [rows[i:i + 2] for i in range(0, len(rows), 2)]})
    return {
        "detailed": True,
        "vitals_full": vitals_full, "complaints_full": complaints, "diagnoses_full": diagnoses,
        "history_notes": visit.history_notes, "examination_notes": visit.examination_notes,
        "exams": exams, "prakriti": prakriti,
        "conditions": [_condition(c, lang, w) for c in patient.conditions.select_related("condition")],
        "allergies": [a.allergen for a in patient.allergies.all()],
        "medications": [" ".join(filter(None, [m.name, m.dose, m.frequency])) for m in patient.medications.all()],
    }


def follow_up_context(visit, lang: str) -> dict:
    w = words_for(lang)
    return {"w": w, "lang": lang, "patient": _patient(visit.patient, w), "date": visit.visit_date,
            "follow_up_date": visit.follow_up_date, "follow_up_notes": visit.follow_up_notes,
            **letterhead(visit.branch, visit.doctor)}


def prakriti_context(visit, exam, lang: str) -> dict:
    w = words_for(lang)
    result = exam.result or {}
    kind = result.get("type", "")
    main = "sama" if kind == "sama" else (kind.split("_")[0] if kind else "")
    return {
        "w": w, "lang": lang, "patient": _patient(visit.patient, w), "date": visit.visit_date,
        "bars": [{"key": d, "name": w[d], "percent": result.get(d, 0)} for d in ("vata", "pitta", "kapha")],
        "type_name": " - ".join(w.get(part, part) for part in kind.split("_")) if kind and kind != "sama" else w["sama"],
        "answered": result.get("answered", 0), "total": result.get("total", 0),
        "guidance": PRAKRITI_GUIDANCE.get(lang, PRAKRITI_GUIDANCE["en"]).get(main, ""),
        **letterhead(visit.branch, visit.doctor),
    }


def certificate_context(certificate, lang: str) -> dict:
    w = words_for(lang)
    return {"w": w, "lang": lang, "patient": _patient(certificate.patient, w), "certificate": certificate,
            "title": w[f"{certificate.kind}_title"], "date": certificate.issued_on,
            **letterhead(certificate.branch, certificate.doctor)}
