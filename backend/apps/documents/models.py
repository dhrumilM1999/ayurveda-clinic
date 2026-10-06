"""
Print-outs (PDF) of medical documents. ASK FIRST before changing these models.

- IssuedDocument: one row per document that was printed (prescription, certificate, follow-up card,
  Prakriti report). It holds the document number, the secret code used in the QR "is this genuine?" page,
  and how often it was printed (the 2nd print onwards says DUPLICATE COPY). Never deleted.
- Certificate: a medical (rest advised) or fitness certificate written by a doctor. Never deleted; a wrong
  one is cancelled (the verify page then says "cancelled").
"""
import secrets

from django.conf import settings
from django.db import models

from apps.common.fields import EncryptedTextField
from apps.common.models import BranchScopedModel

DOCUMENT_KINDS = [
    ("prescription", "Prescription"),
    ("certificate", "Certificate"),
    ("follow_up_card", "Follow-up card"),
    ("prakriti_report", "Prakriti report"),
]
CERTIFICATE_KINDS = [
    ("medical", "Medical certificate (rest advised)"),
    ("fitness", "Fitness certificate"),
    ("general", "Certificate (other)"),
]


def new_token() -> str:
    return secrets.token_urlsafe(16)


class IssuedDocument(BranchScopedModel):
    kind = models.CharField(max_length=20, choices=DOCUMENT_KINDS)
    object_id = models.CharField(max_length=64)  # the prescription / certificate / visit it was made from
    number = models.CharField(max_length=40, blank=True)
    token = models.CharField(max_length=40, unique=True, default=new_token)
    patient = models.ForeignKey("patients.Patient", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    issued_on = models.DateField()
    print_count = models.PositiveIntegerField(default=0)
    last_printed_at = models.DateTimeField(null=True, blank=True)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "object_id"], condition=models.Q(is_deleted=False),
                                    name="uniq_issued_document"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.number}"


class Certificate(BranchScopedModel):
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="certificates")
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    visit = models.ForeignKey("emr.Visit", null=True, blank=True, on_delete=models.PROTECT, related_name="certificates")
    kind = models.CharField(max_length=20, choices=CERTIFICATE_KINDS, default="medical")
    number = models.CharField(max_length=40)
    issued_on = models.DateField(db_index=True)
    diagnosis = EncryptedTextField(blank=True)
    rest_from = models.DateField(null=True, blank=True)
    rest_to = models.DateField(null=True, blank=True)
    fit_from = models.DateField(null=True, blank=True)  # fitness: fit to resume work / school from
    remarks = EncryptedTextField(blank=True)
    is_cancelled = models.BooleanField(default=False)
    cancel_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-issued_on", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "number"], name="uniq_certificate_number_per_branch"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} {self.number}"
