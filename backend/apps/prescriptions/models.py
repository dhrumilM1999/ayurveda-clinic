"""
Prescriptions (Rx) written at a check-up, and disease-wise prescription templates.
ASK FIRST before changing these models (it changes the database).

- One prescription per check-up (visit). It belongs to the branch of the visit.
- Each line keeps a COPY of the medicine's name, form and version, so an old prescription always shows
  exactly what was prescribed, even if the medicine list changes later.
- Status: "draft" while the doctor is writing; "final" when the check-up is completed (the pharmacy
  dispenses final prescriptions).
- Prescriptions are never deleted.
"""
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.common.models import BranchScopedModel, OrgScopedModel

STATUS_CHOICES = [("draft", "Being written"), ("final", "Final")]
DURATION_UNITS = [("days", "days"), ("weeks", "weeks"), ("months", "months")]


class Prescription(BranchScopedModel):
    visit = models.OneToOneField("emr.Visit", on_delete=models.PROTECT, related_name="prescription")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="prescriptions")
    doctor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="prescriptions")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft", db_index=True)
    notes = EncryptedTextField(blank=True)  # general instructions for the patient
    # How many days the medicines continue (quick choice for all lines; each line keeps its own duration)
    medicine_days = models.PositiveSmallIntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Prescription for {self.patient.full_name} ({self.created_at:%d-%m-%Y})"


class PrescriptionItem(OrgScopedModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name="items")
    medicine = models.ForeignKey("medicines.Medicine", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    # Copies taken when prescribed (the medicine list may change later)
    medicine_name = models.CharField(max_length=200)
    medicine_kind = models.CharField(max_length=20, blank=True)
    medicine_version = models.PositiveIntegerField(null=True, blank=True)
    dosage_form = models.CharField(max_length=100, blank=True)

    dose = models.CharField(max_length=20, blank=True)  # e.g. "2", "1/2", "3-5"
    dose_unit = models.CharField(max_length=40, blank=True)  # e.g. "tablet", "g"
    frequency = models.CharField(max_length=20, blank=True)  # morning-noon-night, e.g. "1-0-1"
    timing = models.CharField(max_length=60, blank=True)  # e.g. "After food"
    anupana = models.CharField(max_length=60, blank=True)  # e.g. "Warm water"
    duration = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_unit = models.CharField(max_length=10, choices=DURATION_UNITS, default="days")
    quantity = models.CharField(max_length=40, blank=True)  # e.g. "1 bottle", "60 tablets"
    instructions = models.CharField(max_length=300, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "created_at"]

    @property
    def patient_id(self):
        return self.prescription.patient_id


class PrescriptionTemplate(OrgScopedModel):
    """A ready set of medicines for a disease, e.g. "Amlapitta - standard"."""

    name = models.CharField(max_length=150)
    diagnosis = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    # [{"medicine": "<id>", "dose", "dose_unit", "frequency", "timing", "anupana", "duration", "duration_unit",
    #   "instructions"}]
    items = models.JSONField(default=list)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


def _private_storage():
    from django.core.files.storage import storages

    return storages["private"]


def handwriting_path(instance, filename):
    """Saved under a random name, so the file name never shows patient details."""
    import uuid

    return f"patients/{instance.patient_id}/handwriting/{uuid.uuid4().hex}.png"


class HandwrittenPrescription(BranchScopedModel):
    """
    A prescription the doctor wrote by hand on the digital pad (or any pen screen).
    - `ink`: only the handwriting (transparent PNG).
    - `image`: ONE picture = the clinic letterhead + patient details + the handwriting + signature and QR.
    A doctor may write several pages for one check-up. Never deleted (a mistake is replaced by a new page and the
    old one is marked removed). Private storage only; every view is written to the audit log.
    """

    visit = models.ForeignKey("emr.Visit", on_delete=models.PROTECT, related_name="handwritten_prescriptions")
    prescription = models.ForeignKey(Prescription, null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="handwritten_pages")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="handwritten_prescriptions")
    doctor = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    paper = models.CharField(max_length=4, default="a5")  # a5 or a4: the page the combined picture was made for
    ink = models.FileField(storage=_private_storage, upload_to=handwriting_path)
    image = models.FileField(storage=_private_storage, upload_to=handwriting_path, blank=True)
    number = models.CharField(max_length=40, blank=True)  # the Rx number printed on the page
    width_px = models.PositiveIntegerField(default=0)
    height_px = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["branch", "created_at"])]
