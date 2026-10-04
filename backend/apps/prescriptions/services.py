"""
Prescription rules: saving the lines (with a copy of the medicine details), safety check, finalizing.
Other modules (check-up, pharmacy, printing) should use these functions.
"""
from django.db import transaction
from django.utils import timezone

from apps.medicines.models import Medicine

from .models import Prescription, PrescriptionItem
from .safety import check_prescription

LINE_FIELDS = ["dose", "dose_unit", "frequency", "timing", "anupana", "duration", "duration_unit", "quantity",
               "instructions"]


def lines_for_check(items) -> list[dict]:
    """Prescription items (model rows or cleaned dicts) -> input for the safety rules."""
    result = []
    for item in items:
        get = item.get if isinstance(item, dict) else (lambda k, i=item: getattr(i, k))
        result.append({
            "medicine": get("medicine"), "medicine_name": get("medicine_name"),
            "duration": get("duration"), "duration_unit": get("duration_unit"),
        })
    return result


def warnings_for(prescription: Prescription) -> list[dict]:
    items = prescription.items.select_related("medicine")
    return check_prescription(prescription.patient, lines_for_check(items))


@transaction.atomic
def save_prescription(visit, items: list[dict], notes, user, prescription: Prescription | None = None) -> Prescription:
    """
    Create or update the prescription of a check-up. `items` are cleaned lines (see serializers).
    Lines keep their id when edited, new lines are added, removed lines are soft-deleted.
    """
    if prescription is None:
        prescription = Prescription.objects.filter(visit=visit).first()
    if prescription is None:
        prescription = Prescription.objects.create(
            organization_id=visit.organization_id, branch=visit.branch, visit=visit, patient=visit.patient,
            doctor=visit.doctor, created_by=user, updated_by=user,
        )
    if notes is not None:
        prescription.notes = notes
    prescription.updated_by = user
    prescription.save()

    existing = {str(row.id): row for row in prescription.items.all()}
    keep = set()
    for order, line in enumerate(items):
        row = existing.get(str(line.get("id") or ""))
        if row is None:
            row = PrescriptionItem(organization_id=prescription.organization_id, prescription=prescription,
                                   created_by=user)
        medicine: Medicine | None = line.get("medicine")
        if medicine is not None and (row.medicine_id != medicine.id or row.medicine_version != medicine.version):
            # Copy the medicine's details as they are now
            row.medicine = medicine
            row.medicine_name = medicine.name
            row.medicine_kind = medicine.kind
            row.medicine_version = medicine.version
            row.dosage_form = medicine.dosage_form.label if medicine.dosage_form_id else ""
        elif medicine is None:
            row.medicine = None
            row.medicine_name = line["medicine_name"]
            row.medicine_kind = ""
            row.medicine_version = None
            row.dosage_form = line.get("dosage_form", "")
        for field in LINE_FIELDS:
            if field in line:
                setattr(row, field, line[field])
        row.sort_order = order
        row.updated_by = user
        row.save()
        keep.add(str(row.id))
    for row_id, row in existing.items():
        if row_id not in keep:
            row.delete(user=user)
    return prescription


def finalize_for_visit(visit, user):
    """Called when the check-up is completed: the prescription becomes final (ready for the pharmacy)."""
    prescription = Prescription.objects.filter(visit=visit).first()
    if prescription and prescription.status != "final" and prescription.items.exists():
        prescription.status = "final"
        prescription.finalized_at = timezone.now()
        prescription.updated_by = user
        prescription.save(update_fields=["status", "finalized_at", "updated_by", "updated_at"])
    return prescription
