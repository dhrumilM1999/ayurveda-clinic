"""
Medicine labels: one small label per medicine, printed as a PDF (one label per page, for label printers).

- From a sale (dispense): batch, expiry, price and quantity given are known.
- From a prescription: for clinics that give medicines without the pharmacy screen (no batch / price).
Which optional fields are printed comes from Additional settings (label_* switches); the label format
(compact / standard / detailed) is the organization's default unless the screen asks for another.
The words on the label follow the patient's language. The template is templates/documents/medicine_label.html.
"""
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.accounts.permissions import BranchPermission
from apps.accounts.services import user_has_perm
from apps.audit.services import log_action
from apps.common.services import translated_master
from apps.organizations.services import branch_features, organization_choices
from apps.prescriptions.models import Prescription

from .models import Dispense

FORMATS = {  # width, height of one label
    "compact": ("50mm", "25mm"),
    "standard": ("75mm", "50mm"),
    "detailed": ("100mm", "70mm"),
}

# Fixed words in the patient's language (medicine names and doctor's instructions stay as written)
WORDS = {
    "en": {"morning": "Morning", "noon": "Noon", "night": "Night", "days": "days", "qty": "Qty", "exp": "Exp",
           "batch": "Batch", "mrp": "MRP", "dr": "Dr", "date": "Date", "rx": "Rx", "dose": "Dose", "for": "For",
           "pack": "pack"},
    "gu": {"morning": "સવાર", "noon": "બપોર", "night": "રાત", "days": "દિવસ", "qty": "જથ્થો", "exp": "એક્સપાયરી",
           "batch": "બેચ", "mrp": "MRP", "dr": "ડૉ.", "date": "તારીખ", "rx": "Rx", "dose": "માત્રા", "for": "માટે",
           "pack": "પેક"},
    "hi": {"morning": "सुबह", "noon": "दोपहर", "night": "रात", "days": "दिन", "qty": "मात्रा", "exp": "एक्सपायरी",
           "batch": "बैच", "mrp": "MRP", "dr": "डॉ.", "date": "तारीख", "rx": "Rx", "dose": "खुराक", "for": "के लिए",
           "pack": "पैक"},
}
UNITS = {"days": {"en": "days", "gu": "દિવસ", "hi": "दिन"}, "weeks": {"en": "weeks", "gu": "અઠવાડિયા", "hi": "हफ़्ते"},
         "months": {"en": "months", "gu": "મહિના", "hi": "महीने"}}


_translated = translated_master  # dropdown word in the patient's language


def _times(frequency: str):
    """'1-0-1' -> [('morning', '1'), ('noon', '0'), ('night', '1')]; anything else -> None."""
    parts = [p.strip() for p in (frequency or "").split("-")]
    if len(parts) != 3 or not all(parts):
        return None
    return list(zip(("morning", "noon", "night"), parts))


def _doctor(name: str, title: str) -> str:
    """'Asha Mehta' -> 'Dr Asha Mehta' (in the label's language); names that already start with Dr stay as they are."""
    return name if name.lower().replace(".", "").startswith("dr ") or name.startswith(title) else f"{title} {name}"


def _qr(text: str) -> str:
    import segno

    return segno.make(text, error="m").svg_data_uri(scale=2, border=1)


def _label_for(item, *, prescription, lang, show, dispense_item=None, number=""):
    medicine = item.medicine if item else (dispense_item.medicine if dispense_item else None)
    org_id = prescription.organization_id
    duration, unit = (item.duration, item.duration_unit) if item and item.duration else (prescription.medicine_days, "days")
    instructions = ", ".join(filter(None, [
        _translated(org_id, "medicine_timing", item.timing, lang) if item else "",
        _translated(org_id, "anupana", item.anupana, lang) if item else "",
        item.instructions if item else "",
    ]))
    if dispense_item is not None:
        qty_value = dispense_item.loose_units or dispense_item.quantity
        if dispense_item.loose_units and medicine.dose_unit_id:
            unit = _translated(org_id, "dose_unit", medicine.dose_unit.label, lang)
        elif medicine.pack_type_id:
            unit = _translated(org_id, "pack_type", medicine.pack_type.label, lang)
        else:
            unit = WORDS[lang]["pack"]
        quantity = f"{qty_value.normalize():f} {unit}"
    else:
        quantity = item.quantity if item else ""
    batch = dispense_item.batch if dispense_item is not None else None
    code_text = (medicine.barcode if medicine and medicine.barcode else f"{number or prescription.id}|{item.medicine_name if item else medicine.name}")
    return {
        "medicine": item.medicine_name if item else medicine.name,
        "strength": medicine.strength if medicine else "",
        "dose": f"{item.dose} {_translated(org_id, 'dose_unit', item.dose_unit, lang)}".strip() if item else "",
        "frequency": item.frequency if item else "",
        "times": _times(item.frequency) if item and show["label_times"] else None,
        "duration": f"{duration} {UNITS.get(unit, UNITS['days'])[lang]}" if duration else "",
        "instructions": instructions,
        "quantity": quantity if show["label_quantity"] else "",
        "batch": batch.batch_no if batch and show["label_batch"] and show["pharmacy_batch_tracking"] else "",
        "expiry": batch.expiry_date if batch and batch.expiry_date and show["label_expiry"] and show["pharmacy_expiry_tracking"] else None,
        "price": (dispense_item.mrp if dispense_item is not None else (medicine.mrp if medicine else None))
        if show["label_price"] and show["pharmacy_selling_price"] else None,
        "qr": _qr(code_text) if show["label_code"] else "",
    }


def build_labels(*, prescription, dispense=None, item_ids=None):
    """The label data for a sale (dispense) or a prescription. item_ids: only these lines."""
    branch = prescription.branch
    show = branch_features(branch)
    lang = prescription.patient.preferred_language if prescription.patient.preferred_language in WORDS else "en"
    number = ""
    if dispense is not None:
        from apps.billing.services import invoice_for_dispense

        invoice = invoice_for_dispense(dispense)
        number = invoice.number if invoice else ""
        sources = [(d.prescription_item, d) for d in dispense.items.select_related(
            "medicine__dose_unit", "medicine__pack_type", "batch", "prescription_item")]
        day = timezone.localtime(dispense.created_at).date()
    else:
        sources = [(i, None) for i in prescription.items.select_related("medicine")]
        day = timezone.localdate()
    if item_ids:
        wanted = {str(x) for x in item_ids}
        sources = [(i, d) for i, d in sources if str((d or i).id) in wanted]
    if not sources:
        raise ValidationError({"detail": "There are no medicines to print."})
    labels = [_label_for(i, prescription=prescription, lang=lang, show=show, dispense_item=d, number=number)
              for i, d in sources]
    org = branch.organization
    return {
        "labels": labels, "words": WORDS[lang], "show": show, "date": day, "rx_number": number,
        "patient": prescription.patient.full_name, "doctor": _doctor(prescription.doctor.full_name, WORDS[lang]["dr"]),
        "clinic": org.name, "branch": branch, "rx_short": str(prescription.id)[:8].upper(),
    }


def render_labels(data, label_format: str) -> bytes:
    from weasyprint import HTML

    width, height = FORMATS[label_format]
    html = render_to_string("documents/medicine_label.html", {**data, "format": label_format, "width": width, "height": height})
    return HTML(string=html).write_pdf()


class MedicineLabelView(APIView):
    """
    GET /medicine-labels/?dispense=<id> | ?prescription=<id>  [&layout=compact|standard|detailed] [&items=id,id]
    ("layout", not "format": the API keeps ?format= for itself.)
    Returns the labels as a PDF. Needs "Medicine labels" switched on (Additional settings).
    """

    permission_classes = [IsAuthenticated, BranchPermission]
    branch_scoped = True

    def get(self, request):
        from apps.billing.views import pdf_response

        branch, p = request.branch, request.query_params
        if not branch_features(branch).get("medicine_labels"):
            raise PermissionDenied("Medicine labels are switched off (Additional settings).")
        label_format = p.get("layout") or organization_choices(request.user.organization_id)["label_format"]
        if label_format not in FORMATS:
            raise ValidationError({"layout": "Choose compact, standard or detailed."})
        dispense = None
        if p.get("dispense"):
            if not user_has_perm(request.user, "pharmacy.view", branch):
                raise PermissionDenied()
            dispense = Dispense.objects.filter(branch=branch, pk=p["dispense"]).select_related(
                "prescription__patient", "prescription__doctor", "prescription__branch__organization").first()
            if dispense is None:
                raise NotFound("Sale not found.")
            if dispense.prescription_id is None:
                raise ValidationError({"detail": "Patient labels need a prescription; a counter sale has none."})
            prescription = dispense.prescription
        elif p.get("prescription"):
            if not (user_has_perm(request.user, "prescriptions.view", branch) or user_has_perm(request.user, "pharmacy.view", branch)):
                raise PermissionDenied()
            prescription = Prescription.objects.filter(branch=branch, pk=p["prescription"]).select_related(
                "patient", "doctor", "branch__organization").first()
            if prescription is None:
                raise NotFound("Prescription not found.")
        else:
            raise ValidationError({"detail": "Give a sale (dispense) or a prescription."})
        items = [x for x in p.get("items", "").split(",") if x]
        data = build_labels(prescription=prescription, dispense=dispense, item_ids=items or None)
        log_action(request, "print", dispense or prescription, changes={
            "labels": len(data["labels"]), "format": label_format, "patient": str(prescription.patient_id)})
        return pdf_response(render_labels(data, label_format), f"labels-{data['rx_short']}.pdf", p.get("download") == "1")
