"""
The live preview of PDF settings (Settings -> PDF settings).

preview_pdf() makes the REAL PDF of a document with settings that are NOT saved yet (they come from the screen).
It uses the newest real record of that kind in the branch when there is one; otherwise a clearly fictional sample
("Sample Patient"). Nothing is saved: no document number is used up and no print is counted.
SAFE TO EDIT: the sample texts in the sample_* functions. ASK FIRST before changing the rest.
"""
from datetime import date, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

from django.conf import settings
from django.utils import timezone

from .print_settings import DOC_TYPES, is_bill, page_settings
from .services import (
    SIZES, certificate_context, follow_up_context, language_of, letterhead, prakriti_context, prescription_context,
    render, therapy_plan_context, _qr,
)
from .words import CASE_SHEET_LINES, CASE_SHEET_SPLIT_BEFORE, CASE_SHEET_WORDS, PRAKRITI_GUIDANCE, words_for

TODAY = timezone.localdate


def _doctor():
    return SimpleNamespace(full_name="Dr. Sample Doctor", qualification="BAMS, MD (Ayurveda)", registration_number="G-00000", signature=None)


def _patient_dict(w):
    return {"name": "Sample Patient", "uhid": "SAMPLE-1", "age": 42, "gender": w.get("male", "")}


# --- Sample (fictional) documents -------------------------------------------------------------------
def sample_prescription(branch, lang):
    w = words_for(lang)
    items = [
        {"name": "Triphala Churna", "form": "Churna", "strength": "", "dose": "3 g", "frequency": "1-0-1", "times": ["1", "0", "1"],
         "timing": "After food", "anupana": "Warm water", "with_anupana": w["with_x"].format(x="Warm water"),
         "duration": "15 days", "quantity": 1, "instructions": ""},
        {"name": "Ashwagandha Vati", "form": "Vati", "strength": "500 mg", "dose": "1 tablet", "frequency": "1-0-1",
         "times": ["1", "0", "1"], "timing": "After food", "anupana": "", "with_anupana": "", "duration": "30 days",
         "quantity": 60, "instructions": "Sample instruction text"},
    ]
    return {
        "w": w, "lang": lang, "patient": _patient_dict(w), "date": TODAY(), "token": 7,
        "vitals": {"bp": "120/80", "pulse": 72, "weight": 62, "temperature": ""},
        "complaints": ["Joint pain", "Poor appetite"], "diagnoses": ["Sandhivata"], "items": items,
        "notes": "This is a sample prescription for previewing the print design.",
        "advice": ["Warm water", "Light food"], "advice_notes": "", "follow_up_date": TODAY() + timedelta(days=15),
        "follow_up_notes": "", **letterhead(branch, _doctor()),
    }


def sample_case_sheet(branch, lang):
    return {
        "case_lines": [(label, "Sample" if label == "Agni" else "") for label, _ in CASE_SHEET_LINES],
        "split_before": CASE_SHEET_SPLIT_BEFORE, "cs": CASE_SHEET_WORDS, "allergies": [], "weight": "62 kg",
        "complaint_lines": [{"label": "Joint pain", "duration": "2 weeks"}, {"label": "Poor appetite", "duration": ""}],
        "subtitle": branch.print_subtitle, "closed_note": branch.print_closed_note,
        "services": [s.strip() for s in branch.print_services.replace("|", "।").split("।") if s.strip()],
        "quote": branch.print_quote,
    }


def sample_follow_up(branch, lang):
    w = words_for(lang)
    return {"w": w, "lang": lang, "patient": _patient_dict(w), "date": TODAY(), "follow_up_date": TODAY() + timedelta(days=15),
            "follow_up_notes": "Sample note", **letterhead(branch, _doctor())}


def sample_lab_order(branch, lang):
    w = words_for(lang)
    return {"w": w, "lang": lang, "patient": _patient_dict(w), "date": TODAY(), "lab": "Sample Lab", "urgent": False,
            "tests": [{"name": "CBC", "note": "fasting"}, {"name": "LFT", "note": ""}], **letterhead(branch, _doctor())}


def sample_prakriti(branch, lang):
    w = words_for(lang)
    return {
        "w": w, "lang": lang, "patient": _patient_dict(w), "date": TODAY(),
        "bars": [{"key": d, "name": w[d], "percent": p} for d, p in (("vata", 45), ("pitta", 35), ("kapha", 20))],
        "type_name": f"{w['vata']} - {w['pitta']}", "answered": 24, "total": 24,
        "guidance": PRAKRITI_GUIDANCE.get(lang, PRAKRITI_GUIDANCE["en"]).get("vata", ""), **letterhead(branch, _doctor()),
    }


def sample_certificate(branch, lang):
    w = words_for(lang)
    certificate = SimpleNamespace(kind="medical", number="MC-SAMPLE", issued_on=TODAY(), diagnosis="Sample diagnosis",
                                  rest_from=TODAY(), rest_to=TODAY() + timedelta(days=3), fit_from=None, remarks="")
    return {"w": w, "lang": lang, "patient": _patient_dict(w), "certificate": certificate, "title": w["medical_title"],
            "date": TODAY(), **letterhead(branch, _doctor())}


def sample_therapy_plan(branch, lang):
    w = words_for(lang)
    items = [{"name": "Abhyanga", "stage": "pradhana", "sessions": 7, "instructions": "Sample: do not bathe in cold water for 2 hours.", "notes": ""},
             {"name": "Shirodhara", "stage": "pradhana", "sessions": 7, "instructions": "", "notes": ""}]
    sessions = [{"date": TODAY() + timedelta(days=i), "start": time(10, 0), "end": time(11, 0), "therapy": "Abhyanga",
                 "therapist": "Sample Therapist", "room": "Room 1"} for i in range(3)]
    plan = SimpleNamespace(title="Sample therapy plan", consent_taken=False, consent_on=None)
    return {"w": w, "lang": lang, "patient": _patient_dict(w), "date": TODAY(), "plan": plan, "items": items, "sessions": sessions,
            "has_instructions": True, **letterhead(branch, _doctor())}


class _Rows(list):
    def all(self):
        return self


def sample_bill(branch, doc_type):
    """(invoice, credit_note or None) as plain objects with the same names a real bill has."""
    pharmacy = doc_type != "opd_bill"
    if pharmacy:
        rows = [("Triphala Churna 100 g", "TC-001", "2027-06-01", "3004", 2, "pack", 120, 12), ("Ashwagandha Vati 60 tab", "AV-014", "2027-03-01", "3004", 1, "pack", 240, 12)]
    else:
        rows = [("Consultation", "", None, "999312", 1, "visit", 300, 0)]
    lines, total = _Rows(), Decimal(0)
    for desc, batch, exp, hsn, qty, unit, price, gst in rows:
        amount = Decimal(qty * price)
        tax = amount * Decimal(gst) / Decimal(100 + gst) if gst else Decimal(0)
        lines.append(SimpleNamespace(
            description=desc, batch_no=batch, expiry_date=date.fromisoformat(exp) if exp else None, hsn_code=hsn,
            quantity=Decimal(qty), unit_label=unit, unit_price=Decimal(price), discount_percent=Decimal(0), gst_rate=Decimal(gst),
            total_amount=amount, taxable_amount=amount - tax, cgst_amount=tax / 2, sgst_amount=tax / 2))
        total += amount
    patient = SimpleNamespace(uhid="SAMPLE-1", mobile="")
    invoice = SimpleNamespace(
        branch=branch, lines=lines, prescription_id=None, series="PH" if pharmacy else "OP", customer_name="Sample Patient",
        patient=patient, doctor=SimpleNamespace(full_name="Dr. Sample Doctor"), appointment=None, number="SAMPLE/0001", invoice_date=TODAY(),
        place_of_supply=branch.state, gross_amount=total, discount_amount=Decimal(0),
        taxable_amount=sum(l.taxable_amount for l in lines), cgst_amount=sum(l.cgst_amount for l in lines),
        sgst_amount=sum(l.sgst_amount for l in lines), round_off=Decimal(0), total_amount=total, paid_amount=total // 2,
        credited_amount=Decimal(0), balance=total - total // 2, print_count=0)
    note = None
    if doc_type == "credit_note":
        note = SimpleNamespace(
            number="SAMPLE/CN-0001", note_date=TODAY(), total_amount=lines[0].total_amount, taxable_amount=lines[0].taxable_amount,
            cgst_amount=lines[0].cgst_amount, sgst_amount=lines[0].sgst_amount, refund_amount=lines[0].total_amount,
            get_refund_mode_display="Cash", lines=_Rows([SimpleNamespace(invoice_line=lines[0], quantity=lines[0].quantity, total_amount=lines[0].total_amount)]))
        invoice.series = "PH"
    return invoice, note


def sample_report(branch):
    return {
        "columns": [{"key": "day", "label": "Date", "type": "date"}, {"key": "bills", "label": "Bills", "type": "int"},
                    {"key": "amount", "label": "Amount", "type": "money"}],
        "rows": [{"day": TODAY() - timedelta(days=i), "bills": 8 - i, "amount": Decimal(2400 - 150 * i)} for i in range(5)],
        "totals": {"bills": 30, "amount": Decimal(10500)},
    }


def sample_medicine_labels(branch, lang, label_format):
    from apps.pharmacy.labels import WORDS

    words = WORDS[lang]
    show = {k: True for k in ("label_clinic", "label_date", "label_rx_no", "label_patient", "label_doctor", "label_times")}
    labels = [{"medicine": "Triphala Churna", "strength": "100 g", "dose": "3 g", "frequency": "1-0-1",
               "times": [("morning", "1"), ("noon", "0"), ("night", "1")], "duration": "15 " + words["days"],
               "instructions": "After food, with warm water", "quantity": "1 pack", "batch": "TC-001", "expiry": date(2027, 6, 1),
               "price": Decimal("120"), "qr": _qr("SAMPLE")}]
    return {"labels": labels, "words": words, "show": show, "date": TODAY(), "rx_number": "", "patient": "Sample Patient",
            "doctor": "Dr. Sample Doctor", "clinic": branch.organization.name, "branch": branch, "rx_short": "SAMPLE"}


def sample_stock_labels(branch, label_format):
    from apps.pharmacy.stock_labels import FORMATS, barcode_svg

    width, height, code_width = FORMATS[label_format]
    label = {"medicine": "Triphala Churna", "strength": "100 g", "pack": "1 pack", "mrp": Decimal("120"), "price": None,
             "gst": Decimal("12"), "hsn": "3004", "batch": "TC-001", "expiry": date(2027, 6, 1), "code": "290000000017",
             "barcode": barcode_svg("290000000017", code_width, 7 if label_format == "compact" else 12)}
    return {"labels": [label], "clinic": branch.organization.name, "branch": branch, "format": label_format, "width": width, "height": height}


# --- The preview itself ----------------------------------------------------------------------------
def _latest(queryset):
    return queryset.order_by("-created_at").first()


def preview_pdf(*, branch, doc_type: str, paper: str | None, lang: str | None, drafts: dict, duplicate: bool, user=None) -> tuple[bytes, str]:
    """-> (the PDF, "real" or "sample"). drafts: {(scope, doc_type): values} not saved yet."""
    from apps.billing.models import CreditNote, Invoice
    from apps.billing.pdf import SIZES as BILL_SIZES, doc_type_of, render_pdf
    from apps.emr.models import Visit, VisitExam
    from apps.prescriptions.models import Prescription
    from apps.therapy.models import TherapyPlan

    from .models import Certificate, IssuedDocument
    from .views import compose

    ps = page_settings(branch, doc_type, paper or None, drafts)
    size = ps["paper"]
    asked = lang or None
    lang = language_of(None, asked, ps)
    qr = _qr(f"{settings.PUBLIC_APP_URL}/verify/preview")
    source = "sample"

    def number_of(kind, record):
        doc = IssuedDocument.objects.filter(kind=kind, object_id=str(record.id)).first()
        return doc.number if doc else "SAMPLE"

    if is_bill(doc_type):
        if size not in BILL_SIZES:
            size = "a4"
            ps = page_settings(branch, doc_type, size, drafts)
        invoice, note = None, None
        if doc_type == "credit_note":
            note = _latest(CreditNote.objects.filter(branch=branch).select_related("invoice"))
            invoice = note.invoice if note else None
        else:
            invoice = _latest(Invoice.objects.filter(branch=branch, series="OP" if doc_type == "opd_bill" else "PH"))
        if invoice is not None:
            source = "real"
            upi = None
        else:
            invoice, note = sample_bill(branch, doc_type)
            upi = f"upi://pay?pa={branch.upi_vpa or 'clinic@upi'}&pn=Sample&am=100&tn=SAMPLE"
        return render_pdf(invoice=invoice, credit_note=note, size=size, duplicate=duplicate, ps=ps, upi_link=upi), source

    if size not in SIZES:
        size = DOC_TYPES.get(doc_type, {}).get("paper") or "a4"
        ps = page_settings(branch, doc_type, size, drafts)

    if doc_type == "report":
        from apps.reports.exports import to_pdf

        return to_pdf(sample_report(branch), title="Sample report", subtitle=f"{branch.name} · sample figures", organization=branch.organization,
                      notes="Fictional figures, only to show the design.", ps=ps), "sample"

    if doc_type in ("medicine_label", "stock_label"):
        from apps.pharmacy.labels import FORMATS as LABEL_FORMATS, build_labels, render_labels
        from apps.pharmacy.stock_labels import render_stock_labels
        from apps.organizations.services import organization_choices

        choices = organization_choices(branch.organization_id)
        if doc_type == "stock_label":
            fmt = choices.get("stock_label_format", "standard")
            return render_stock_labels(sample_stock_labels(branch, fmt), ps), "sample"
        fmt = choices.get("label_format", "standard")
        if fmt not in LABEL_FORMATS:
            fmt = "standard"
        rx = _latest(Prescription.objects.filter(branch=branch).select_related("patient", "doctor", "branch__organization"))
        data = None
        if rx is not None:
            try:
                data, source = build_labels(prescription=rx), "real"
            except Exception:  # a prescription without medicines: use the sample
                data = None
        return render_labels(data or sample_medicine_labels(branch, lang, fmt), fmt, ps), source

    # Medical documents
    kind = {"prescription": "prescription", "follow_up_card": "follow_up_card", "prakriti_report": "prakriti_report",
            "certificate": "certificate", "therapy_plan": "therapy_plan", "lab_order": "lab-order"}[doc_type]
    record, make, template, number = None, None, None, "SAMPLE"
    if doc_type == "prescription":
        record = _latest(Prescription.objects.filter(branch=branch).select_related("visit__appointment", "patient", "doctor", "branch__organization"))
        template = "prescription.html"
        make = (lambda lng: prescription_context(record, lng)) if record else (lambda lng: sample_prescription(branch, lng))
    elif doc_type == "follow_up_card":
        record = _latest(Visit.objects.filter(branch=branch, follow_up_date__isnull=False).select_related("patient", "doctor", "branch__organization"))
        template = "follow_up_card.html"
        make = (lambda lng: follow_up_context(record, lng)) if record else (lambda lng: sample_follow_up(branch, lng))
    elif doc_type == "prakriti_report":
        exam = _latest(VisitExam.objects.filter(visit__branch=branch, template_code="prakriti").select_related("visit__patient", "visit__doctor", "visit__branch__organization"))
        if exam is not None and (exam.result or {}).get("answered"):
            record = exam
        template = "prakriti_report.html"
        make = (lambda lng: prakriti_context(record.visit, record, lng)) if record else (lambda lng: sample_prakriti(branch, lng))
    elif doc_type == "certificate":
        record = _latest(Certificate.objects.filter(branch=branch).select_related("patient", "doctor", "branch__organization"))
        template = "certificate.html"
        make = (lambda lng: certificate_context(record, lng)) if record else (lambda lng: sample_certificate(branch, lng))
    elif doc_type == "lab_order":  # an order slip is always shown with the sample tests
        template = "lab_order.html"
        make = lambda lng: sample_lab_order(branch, lng)  # noqa: E731
    else:
        record = _latest(TherapyPlan.objects.filter(branch=branch).select_related("patient", "doctor", "branch__organization"))
        template = "therapy_plan.html"
        make = (lambda lng: therapy_plan_context(record, lng)) if record else (lambda lng: sample_therapy_plan(branch, lng))
    if record is not None:
        source = "real"
        number = number_of({"prakriti_report": "prakriti_report"}.get(doc_type, doc_type), record.visit if doc_type == "prakriti_report" else record)
        patient = record.visit.patient if doc_type == "prakriti_report" else record.patient
        lang = language_of(patient, asked, ps)
    template, size, context = compose(
        branch, kind, record if source == "real" else None, template, make, lang=lang, size=size, detailed=False, number=number,
        duplicate=duplicate, qr=qr, cancelled=False, ps=ps)
    return render(template, size, context, ps), source
