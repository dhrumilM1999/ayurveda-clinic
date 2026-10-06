"""
Organization (clinic group) -> Branches -> Rooms.
ASK FIRST before changing these models (it changes the database).
"""
from django.db import models
from django.db.models import Q

from apps.common.models import BaseModel, BranchScopedModel, OrgScopedModel

LANGUAGE_CHOICES = [("en", "English"), ("gu", "Gujarati"), ("hi", "Hindi")]


class Organization(BaseModel):
    """The clinic group. Patients and masters belong here (shared by all branches)."""

    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50, blank=True)
    legal_name = models.CharField(max_length=200, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    logo = models.ImageField(upload_to="logos/", blank=True)
    default_language = models.CharField(max_length=5, choices=LANGUAGE_CHOICES, default="en")
    uhid_prefix = models.CharField(
        "Patient ID prefix", max_length=6, default="AY",
        help_text="Start of every patient ID, e.g. AY -> AY26-000001",
    )
    # Off = the app shows only the main (first) branch: no branch picker, no Branches menu.
    # Data stays branch-wise, so switching it on later needs no data change.
    multi_branch = models.BooleanField(
        "Use more than one branch", default=False,
        help_text="Off: the app works with the main branch only.",
    )

    def main_branch(self):
        """The first branch created (used when multi_branch is off)."""
        return self.branches.filter(is_active=True, is_deleted=False).order_by("created_at").first()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Branch(OrgScopedModel):
    """One clinic location. Visits, appointments, invoices and stock belong to a branch."""

    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="branches")
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, help_text="Short code used in invoice numbers, e.g. AHD")
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, default="Gujarat")
    pincode = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    drug_licence_no = models.CharField("Drug / Ayush licence no. (pharmacy)", max_length=100, blank=True)
    upi_vpa = models.CharField("UPI ID for payments", max_length=100, blank=True, help_text="e.g. clinic@okbank")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "branches"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], condition=Q(is_deleted=False), name="uniq_branch_code_per_org"
            )
        ]

    def __str__(self):
        return self.name


class RoomType(OrgScopedModel):
    """Master list for the 'room type' dropdown (Consultation, Therapy, ...)."""

    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Room(BranchScopedModel):
    name = models.CharField(max_length=100)
    room_type = models.ForeignKey(RoomType, null=True, blank=True, on_delete=models.PROTECT, related_name="rooms")
    capacity = models.PositiveSmallIntegerField(default=1)
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BranchFeatureFlag(BranchScopedModel):
    """Switches a module on/off for one branch. Codes come from features_catalog.py."""

    code = models.CharField(max_length=50)
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"], condition=Q(is_deleted=False), name="uniq_feature_per_branch"
            )
        ]

    def __str__(self):
        return f"{self.branch} / {self.code} = {self.enabled}"


class OrganizationChoice(OrgScopedModel):
    """A chosen option of the organization's additional settings, e.g. label_format = "compact".
    Codes and options: ADDITIONAL_CHOICES."""

    code = models.CharField(max_length=50)
    value = models.CharField(max_length=50)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], condition=Q(is_deleted=False), name="uniq_choice_per_org"
            )
        ]

    def __str__(self):
        return f"{self.organization} / {self.code} = {self.value}"


class OrganizationFeature(OrgScopedModel):
    """An optional extra feature switched on/off for the whole organization. Codes: ADDITIONAL_FEATURES."""

    code = models.CharField(max_length=50)
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"], condition=Q(is_deleted=False), name="uniq_feature_per_org"
            )
        ]

    def __str__(self):
        return f"{self.organization} / {self.code} = {self.enabled}"
