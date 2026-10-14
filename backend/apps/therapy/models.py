"""
Panchakarma and therapy: the list of therapies, a patient's therapy plan, and the booked sessions.
ASK FIRST before changing these models (it changes the database).

- TherapyType: one therapy in the clinic's list (Abhyanga, Shirodhara, Basti, Vamana ...) with its stage
  (Purvakarma = preparation, Pradhanakarma = main procedure, Paschatkarma = after-care), time needed and price.
- TherapyPlan: what the doctor advised for one patient (e.g. "Virechana course"), made of several items.
- TherapyPlanItem: one therapy in the plan and how many sessions are planned.
- TherapySession: one booked sitting: day, time, therapist, room. A therapist or room is never booked twice
  at the same time. The therapist records the oil used and how the patient responded.
- Nothing is deleted (only marked deleted); the patient's notes are stored encrypted like the doctor's notes.
"""
from django.conf import settings
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.common.models import BranchScopedModel, OrgScopedModel

STAGES = [
    ("purva", "Purvakarma (preparation)"),
    ("pradhana", "Pradhanakarma (main procedure)"),
    ("paschat", "Paschatkarma (after-care)"),
    ("other", "Other therapy"),
]
PLAN_STATUSES = [("planned", "Planned"), ("active", "Running"), ("completed", "Completed"), ("cancelled", "Cancelled")]
SESSION_STATUSES = [
    ("scheduled", "Booked"), ("in_progress", "In progress"), ("done", "Done"),
    ("missed", "Patient did not come"), ("cancelled", "Cancelled"),
]
# A session in one of these states still keeps its therapist and room busy
BUSY_STATUSES = ("scheduled", "in_progress", "done")


class TherapyType(OrgScopedModel):
    name = models.CharField(max_length=150)
    name_gu = models.CharField("Name (Gujarati)", max_length=150, blank=True)
    name_hi = models.CharField("Name (Hindi)", max_length=150, blank=True)
    stage = models.CharField(max_length=10, choices=STAGES, default="pradhana")
    duration_minutes = models.PositiveSmallIntegerField(default=45)
    # What is normally used, e.g. "Sesame oil" or "Dhanyamla"; the therapist can change it for a patient
    default_material = models.CharField(max_length=150, blank=True)
    # Shown on the plan print: what the patient should do before / after
    instructions = models.TextField(blank=True, max_length=1500)
    # The price comes from the "Services & charges" list, so the bill and the plan always agree
    service = models.ForeignKey("billing.ServiceCharge", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_sample = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "name"], condition=models.Q(is_deleted=False),
                                    name="uniq_therapy_name_per_org"),
        ]

    def __str__(self):
        return self.name


class TherapyPlan(BranchScopedModel):
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="therapy_plans")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    visit = models.ForeignKey("emr.Visit", null=True, blank=True, on_delete=models.PROTECT, related_name="therapy_plans")
    title = models.CharField(max_length=150)  # e.g. "Virechana course"
    start_date = models.DateField(db_index=True)
    status = models.CharField(max_length=12, choices=PLAN_STATUSES, default="planned", db_index=True)
    notes = EncryptedTextField(blank=True)
    # The patient agrees to the procedure (needed before Vamana, Virechana, Basti ...)
    consent_taken = models.BooleanField(default=False)
    consent_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        indexes = [models.Index(fields=["branch", "status"]), models.Index(fields=["patient", "start_date"])]

    def __str__(self):
        return f"{self.title} - {self.patient}"


class TherapyPlanItem(OrgScopedModel):
    plan = models.ForeignKey(TherapyPlan, on_delete=models.PROTECT, related_name="items")
    therapy = models.ForeignKey(TherapyType, on_delete=models.PROTECT, related_name="+")
    stage = models.CharField(max_length=10, choices=STAGES, default="pradhana")
    sessions_planned = models.PositiveSmallIntegerField(default=1)
    notes = models.CharField(max_length=250, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "created_at"]


class TherapySession(BranchScopedModel):
    plan = models.ForeignKey(TherapyPlan, on_delete=models.PROTECT, related_name="sessions")
    item = models.ForeignKey(TherapyPlanItem, on_delete=models.PROTECT, related_name="sessions")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="therapy_sessions")
    therapy = models.ForeignKey(TherapyType, on_delete=models.PROTECT, related_name="+")
    therapist = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    room = models.ForeignKey("organizations.Room", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    date = models.DateField(db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(max_length=12, choices=SESSION_STATUSES, default="scheduled", db_index=True)
    # Filled by the therapist
    material_used = models.CharField(max_length=150, blank=True)
    quantity_ml = models.PositiveIntegerField(null=True, blank=True)
    patient_response = EncryptedTextField(blank=True)
    notes = EncryptedTextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["date", "start_time"]
        indexes = [models.Index(fields=["branch", "date"]), models.Index(fields=["therapist", "date"]),
                   models.Index(fields=["room", "date"])]
