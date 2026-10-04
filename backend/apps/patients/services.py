"""Functions for patients: patient IDs, consent status, upload checks. ASK FIRST before editing."""
import io

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from PIL import Image
from rest_framework.exceptions import ValidationError

from .consent_catalog import CONSENT_PURPOSES
from .models import ConsentPurpose, PatientConsent, UhidSequence


def next_uhid(organization) -> str:
    """
    Next patient ID, e.g. AY26-000001. One running number per organization per calendar year.
    Done inside a database lock, so two receptionists can never get the same number.
    """
    year = timezone.localdate().year
    for _ in range(3):
        try:
            with transaction.atomic():
                seq, _ = UhidSequence.objects.select_for_update().get_or_create(
                    organization=organization, year=year,
                )
                seq.last_number += 1
                seq.save(update_fields=["last_number"])
                break
        except IntegrityError:
            continue  # another request created this year's counter at the same moment; try again
    prefix = (organization.uhid_prefix or "AY").upper()
    return f"{prefix}{year % 100:02d}-{seq.last_number:06d}"


def ensure_consent_purposes(organization) -> int:
    existing = set(ConsentPurpose.all_objects.filter(organization=organization).values_list("code", flat=True))
    added = 0
    for order, info in enumerate(CONSENT_PURPOSES):
        if info["code"] not in existing:
            ConsentPurpose.objects.create(organization=organization, sort_order=order, **info)
            added += 1
    return added


def current_consents(patient) -> dict[str, PatientConsent]:
    """{purpose code: latest consent record} for one patient."""
    latest = {}
    records = PatientConsent.objects.filter(patient=patient).select_related("purpose").order_by("created_at")
    for record in records:
        latest[record.purpose.code] = record
    return latest


def has_consent(patient, purpose_code: str) -> bool:
    record = current_consents(patient).get(purpose_code)
    return bool(record and record.granted)


# --- Upload checks ------------------------------------------------------------
IMAGE_TYPES = {"jpg", "jpeg", "png", "webp"}
DOCUMENT_TYPES = IMAGE_TYPES | {"pdf"}


def check_upload(uploaded, allowed=DOCUMENT_TYPES):
    """Refuse files that are too big, of the wrong type, or not really images/PDFs."""
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    if uploaded.size > max_bytes:
        raise ValidationError({"file": f"File is too large. Maximum is {settings.MAX_UPLOAD_MB} MB."})
    ext = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
    if ext not in allowed:
        raise ValidationError({"file": f"Allowed file types: {', '.join(sorted(allowed))}."})
    head = uploaded.read(2048)
    uploaded.seek(0)
    if ext == "pdf":
        if not head.startswith(b"%PDF"):
            raise ValidationError({"file": "This is not a real PDF file."})
        return "application/pdf"
    try:
        image = Image.open(io.BytesIO(uploaded.read()))
        image.verify()
    except Exception:
        raise ValidationError({"file": "This is not a real image file."})
    finally:
        uploaded.seek(0)
    return {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[ext]
