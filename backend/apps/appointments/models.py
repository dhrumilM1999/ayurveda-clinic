"""
Appointments, walk-ins and the waiting queue.
ASK FIRST before changing these models (it changes the database).

- Appointments belong to a BRANCH (the patient belongs to the whole organization).
- A booked appointment has a time slot; a walk-in has no slot.
- The token number (1, 2, 3...) is given when the patient arrives (check-in), per doctor per day.
- Appointments are never deleted: they are cancelled, and the history is kept.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import BranchScopedModel

STATUS_CHOICES = [
    ("booked", "Booked"),
    ("checked_in", "Waiting"),
    ("in_consultation", "With doctor"),
    ("completed", "Done"),
    ("cancelled", "Cancelled"),
    ("no_show", "Did not come"),
]
# Appointments in these states still need the doctor's time.
ACTIVE_STATUSES = ("booked", "checked_in", "in_consultation")

KIND_CHOICES = [("booked", "Booked appointment"), ("walk_in", "Walk-in")]


class Appointment(BranchScopedModel):
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="appointments")
    date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="booked")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="booked", db_index=True)
    token_number = models.PositiveSmallIntegerField(null=True, blank=True)

    reason = models.CharField("Reason for visit", max_length=200, blank=True)
    notes = models.CharField(max_length=500, blank=True)

    checked_in_at = models.DateTimeField(null=True, blank=True)
    consultation_started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)
    reschedule_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["date", "start_time", "token_number", "created_at"]
        constraints = [
            # No double booking: one doctor, one date, one start time (in any branch),
            # unless the earlier appointment was cancelled.
            models.UniqueConstraint(
                fields=["doctor", "date", "start_time"],
                condition=Q(is_deleted=False, start_time__isnull=False) & ~Q(status="cancelled"),
                name="uniq_appointment_doctor_slot",
            ),
            models.UniqueConstraint(
                fields=["branch", "doctor", "date", "token_number"],
                condition=Q(token_number__isnull=False),
                name="uniq_appointment_token",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "date"]),
            models.Index(fields=["doctor", "date"]),
        ]

    def __str__(self):
        when = self.start_time.strftime("%H:%M") if self.start_time else "walk-in"
        return f"{self.patient.full_name} with {self.doctor.full_name} on {self.date} {when}"


class TokenSequence(models.Model):
    """Running token number per branch, per doctor, per day."""

    branch = models.ForeignKey("organizations.Branch", on_delete=models.PROTECT, related_name="+")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    last_number = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch", "doctor", "date"], name="uniq_token_sequence"),
        ]
