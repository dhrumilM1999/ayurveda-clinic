"""
Online enquiries: people who ask for an appointment or information on the clinic's website (or by phone / at the
desk). They are not patients yet. ASK FIRST before changing these models.

- A visitor fills the public form (/enquiry) -> an Enquiry with status "new".
- The front desk calls or messages them, writes notes, and changes the status; when the person comes, the desk
  registers them as a patient and books the appointment.
- Only what the visitor typed is stored (name, phone, concern, message) plus their consent to be contacted.
"""
from django.db import models

from apps.common.models import OrgScopedModel

STATUS_CHOICES = [
    ("new", "New"),
    ("contacted", "Contacted"),
    ("appointment", "Appointment booked"),
    ("not_interested", "Not interested"),
    ("closed", "Closed"),
]
SOURCE_CHOICES = [("website", "Website"), ("phone", "Phone"), ("walk_in", "Walk-in"), ("other", "Other")]
TIME_CHOICES = [("any", "Any time"), ("morning", "Morning"), ("evening", "Evening")]


class Enquiry(OrgScopedModel):
    branch = models.ForeignKey("organizations.Branch", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    concern = models.CharField("What is the problem about", max_length=200, blank=True)
    message = models.TextField(blank=True, max_length=1000)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=10, choices=TIME_CHOICES, default="any")
    language = models.CharField(max_length=5, default="en")
    source = models.CharField(max_length=12, choices=SOURCE_CHOICES, default="website", db_index=True)
    consent_contact = models.BooleanField("Agreed to be contacted", default=False)

    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="new", db_index=True)
    follow_up_on = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, max_length=2000)
    assigned_to = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    patient = models.ForeignKey("patients.Patient", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    # For spam control only
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.phone})"
