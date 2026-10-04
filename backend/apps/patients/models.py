"""
Patients and everything recorded at registration.
ASK FIRST before changing these models (it changes the database).

- Patients belong to the ORGANIZATION: one patient ID (UHID), full history at every branch.
- Vitals, documents and consents remember the branch where they were recorded.
- Patients are never deleted.
"""
import uuid
from datetime import date

from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.common.fields import EncryptedTextField
from apps.common.models import BaseModel, OrgScopedModel
from apps.organizations.models import LANGUAGE_CHOICES


def private_storage():
    from django.core.files.storage import storages

    return storages["private"]


def patient_file_path(instance, filename):
    """Files are saved under a random name, so the file name never shows patient details."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    patient_id = getattr(instance, "patient_id", None) or instance.pk
    return f"patients/{patient_id}/{uuid.uuid4().hex}.{ext}"


GENDER_CHOICES = [("male", "Male"), ("female", "Female"), ("other", "Other")]


class UhidSequence(models.Model):
    """Running number for patient IDs, one counter per organization per year."""

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT, related_name="+")
    year = models.PositiveSmallIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "year"], name="uniq_uhid_seq_year")]


class Patient(OrgScopedModel):
    uhid = models.CharField("Patient ID (UHID)", max_length=20, editable=False)
    registered_branch = models.ForeignKey(
        "organizations.Branch", on_delete=models.PROTECT, related_name="+", null=True, blank=True,
    )
    registration_date = models.DateField(default=date.today, db_index=True)

    # --- Person ---
    photo = models.FileField(storage=private_storage, upload_to=patient_file_path, blank=True)
    title = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField("Father / husband name", max_length=100, blank=True)
    last_name = models.CharField("Surname", max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    dob_is_estimated = models.BooleanField(default=False, help_text="True if only the age was given")
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    blood_group = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    marital_status = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    preferred_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="gu")
    occupation = models.CharField(max_length=100, blank=True)
    guardian_name = models.CharField(max_length=150, blank=True, help_text="For children")

    # --- Contact ---
    country_code = models.CharField(max_length=5, default="+91")
    mobile = models.CharField(max_length=15, db_index=True)
    alternate_mobile = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    house = models.CharField("House / flat number", max_length=100, blank=True)
    society = models.CharField("Society / apartment", max_length=150, blank=True)
    area = models.CharField("Area / landmark / road", max_length=200, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    state = models.CharField(max_length=100, default="Gujarat", blank=True)
    country = models.CharField(max_length=100, default="India", blank=True)

    # --- Referred by ---
    referral_source = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    referred_by_name = models.CharField(max_length=150, blank=True)
    referred_by_phone = models.CharField(max_length=15, blank=True)

    # --- Emergency contact ---
    emergency_name = models.CharField(max_length=150, blank=True)
    emergency_relation = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    emergency_phone = models.CharField(max_length=15, blank=True)

    # --- Flags ---
    is_vip = models.BooleanField(default=False)
    is_foc = models.BooleanField("Free of charge", default=False)

    # --- History (encrypted free text; needs emr.view to read) ---
    past_history = EncryptedTextField(blank=True)
    family_history = EncryptedTextField(blank=True)
    surgical_history = EncryptedTextField(blank=True)
    other_notes = EncryptedTextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "uhid"], name="uniq_patient_uhid_per_org"),
        ]
        indexes = [
            models.Index(fields=["organization", "registration_date"]),
            models.Index(Lower("first_name"), name="patient_first_name_lower"),
            models.Index(Lower("last_name"), name="patient_last_name_lower"),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.uhid})"

    @property
    def full_name(self) -> str:
        return " ".join(p for p in [self.first_name, self.middle_name, self.last_name] if p)

    @property
    def age_years(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = date.today()
        dob = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def delete(self, *args, **kwargs):
        raise PermissionError("Patients are never deleted.")


class PatientChild(OrgScopedModel):
    """Base for rows that hang off one patient."""

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="+")

    class Meta:
        abstract = True


class PatientCondition(PatientChild):
    """A medical condition from the history checklist (diabetes, BP, ...)."""

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="conditions")
    condition = models.ForeignKey("common.MasterValue", on_delete=models.PROTECT, related_name="+")
    since = models.CharField(max_length=50, blank=True, help_text="e.g. 2019 or 5 years")
    notes = models.CharField(max_length=255, blank=True)


class PatientAllergy(PatientChild):
    SEVERITY = [("mild", "Mild"), ("moderate", "Moderate"), ("severe", "Severe")]

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="allergies")
    allergy_type = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    allergen = models.CharField(max_length=150)
    severity = models.CharField(max_length=10, choices=SEVERITY, default="moderate")
    reaction = models.CharField(max_length=255, blank=True)


class PatientMedication(PatientChild):
    """An allopathic (or other) medicine the patient is currently taking."""

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="medications")
    name = models.CharField(max_length=150)
    dose = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    since = models.CharField(max_length=50, blank=True)
    notes = models.CharField(max_length=255, blank=True)


class PatientVital(PatientChild):
    """BP, pulse, weight ... recorded at one time in one branch. BMI is calculated."""

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="vitals")
    branch = models.ForeignKey("organizations.Branch", on_delete=models.PROTECT, related_name="+")
    recorded_at = models.DateTimeField(db_index=True)
    bp_systolic = models.PositiveSmallIntegerField(null=True, blank=True)
    bp_diastolic = models.PositiveSmallIntegerField(null=True, blank=True)
    pulse = models.PositiveSmallIntegerField(null=True, blank=True)
    temperature_f = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    spo2 = models.PositiveSmallIntegerField("SpO₂ %", null=True, blank=True)
    respiratory_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, editable=False)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-recorded_at"]

    def save(self, *args, **kwargs):
        if self.weight_kg and self.height_cm:
            metres = float(self.height_cm) / 100
            self.bmi = round(float(self.weight_kg) / (metres * metres), 1)
        else:
            self.bmi = None
        super().save(*args, **kwargs)


class PatientDocument(PatientChild):
    """An uploaded report / old prescription / scan. Stored in private storage."""

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="documents")
    branch = models.ForeignKey("organizations.Branch", on_delete=models.PROTECT, related_name="+", null=True)
    document_type = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    title = models.CharField(max_length=200)
    document_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    file = models.FileField(storage=private_storage, upload_to=patient_file_path)
    original_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()

    class Meta:
        ordering = ["-created_at"]


class ConsentPurpose(OrgScopedModel):
    """
    Why we ask for consent (treatment, SMS/WhatsApp, AI, research). The text is shown to the
    patient in their language. Changing the text should raise the version number.
    """

    code = models.SlugField(max_length=50)
    title = models.CharField(max_length=150)
    title_gu = models.CharField(max_length=150, blank=True)
    title_hi = models.CharField(max_length=150, blank=True)
    description = models.TextField()
    description_gu = models.TextField(blank=True)
    description_hi = models.TextField(blank=True)
    is_required = models.BooleanField(default=False, help_text="Needed before treatment can start")
    version = models.PositiveSmallIntegerField(default=1)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], condition=Q(is_deleted=False), name="uniq_consent_purpose_code"
            )
        ]

    def __str__(self):
        return self.title


class PatientConsent(PatientChild):
    """
    One consent event: given or withdrawn, for one purpose. Never changed afterwards;
    the latest event per purpose is the current status. (DPDP Act 2023)
    """

    METHODS = [
        ("signed_form", "Signed paper form"),
        ("verbal", "Verbal, in person"),
        ("on_screen", "Ticked on screen by patient"),
        ("guardian", "Given by parent / guardian"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="consents")
    branch = models.ForeignKey("organizations.Branch", on_delete=models.PROTECT, related_name="+")
    purpose = models.ForeignKey(ConsentPurpose, on_delete=models.PROTECT, related_name="+")
    purpose_version = models.PositiveSmallIntegerField()
    granted = models.BooleanField()
    method = models.CharField(max_length=20, choices=METHODS)
    language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES)
    given_by = models.CharField(max_length=150, blank=True, help_text="If not the patient, e.g. guardian name")
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Consent records cannot be changed. Record a new one instead.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Consent records cannot be deleted.")
