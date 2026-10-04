"""
The doctor's check-up (visit) and Ayurveda examination templates.
ASK FIRST before changing these models (it changes the database).

- A Visit is one check-up of one patient by one doctor in one branch (often linked to an appointment).
- The doctor's notes (complaints, history, diagnosis, advice, exam answers) are stored ENCRYPTED.
- ExamTemplate: an editable form (Ashtavidha, Prakriti...). Starting templates: templates_catalog.py.
- VisitExam: the answers of one template in one visit. It remembers the template version used.
- Visits are never deleted.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.fields import EncryptedJSONField, EncryptedTextField
from apps.common.models import BranchScopedModel, OrgScopedModel

TEMPLATE_KINDS = [("form", "Form"), ("questionnaire", "Questionnaire (scored)")]
VISIT_STATUSES = [("draft", "In progress"), ("completed", "Completed")]


class ExamTemplate(OrgScopedModel):
    code = models.SlugField(max_length=50)
    version = models.PositiveSmallIntegerField(default=1)
    kind = models.CharField(max_length=20, choices=TEMPLATE_KINDS, default="form")
    name = models.CharField(max_length=150)
    name_gu = models.CharField("Name (Gujarati)", max_length=150, blank=True)
    name_hi = models.CharField("Name (Hindi)", max_length=150, blank=True)
    description = models.JSONField(default=dict, blank=True)  # {"en":..., "gu":..., "hi":...}
    fields = models.JSONField(default=list)  # see templates_catalog.py for the shape
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], condition=Q(is_deleted=False),
                                    name="uniq_exam_template_code"),
        ]

    def __str__(self):
        return f"{self.name} (v{self.version})"


class Visit(BranchScopedModel):
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="visits")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="visits")
    appointment = models.OneToOneField(
        "appointments.Appointment", null=True, blank=True, on_delete=models.PROTECT, related_name="visit",
    )
    visit_date = models.DateField(db_index=True)
    status = models.CharField(max_length=20, choices=VISIT_STATUSES, default="draft", db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # --- The doctor's notes (encrypted) ---
    # complaints: [{"label", "code", "duration", "duration_unit", "severity", "notes"}]
    complaints = EncryptedJSONField(default=list, blank=True)
    history_notes = EncryptedTextField("History of present illness / clinical notes", blank=True)
    examination_notes = EncryptedTextField(blank=True)
    # diagnoses: [{"label", "code", "system", "kind": "provisional" | "final"}]
    diagnoses = EncryptedJSONField(default=list, blank=True)
    # advice: ["Drink warm water", ...]
    advice = EncryptedJSONField(default=list, blank=True)
    advice_notes = EncryptedTextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True, db_index=True)
    follow_up_notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-visit_date", "-created_at"]
        indexes = [
            models.Index(fields=["branch", "visit_date"]),
            models.Index(fields=["patient", "visit_date"]),
        ]

    def __str__(self):
        return f"Visit of {self.patient.full_name} on {self.visit_date}"


class VisitExam(OrgScopedModel):
    visit = models.ForeignKey(Visit, on_delete=models.PROTECT, related_name="exams")
    template = models.ForeignKey(ExamTemplate, on_delete=models.PROTECT, related_name="+")
    template_code = models.SlugField(max_length=50)
    template_version = models.PositiveSmallIntegerField()
    values = EncryptedJSONField(default=dict, blank=True)  # {"nadi": "vata", "nadi_rate": 78, ...}
    result = EncryptedJSONField(default=dict, blank=True)  # Prakriti: {"vata": 50, "pitta": 33, ...}

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["visit", "template"], condition=Q(is_deleted=False),
                                    name="uniq_visit_exam_template"),
        ]

    @property
    def patient_id(self):
        # Lets the audit log link exam changes to the patient's Activity tab.
        return self.visit.patient_id
