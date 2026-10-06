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


def letterhead(branch, doctor) -> dict:
    org = branch.organization
    return {
        "organization": org, "branch": branch, "logo": _data_uri(org.logo),
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
