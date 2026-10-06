"""
The medicine list (master), shared by all branches. ASK FIRST before changing these models.

- Two kinds: CLASSICAL (official name from the Ayurvedic Formulary / Pharmacopoeia of India, with reference)
  and PROPRIETARY (patent & proprietary brand, with manufacturer). A brand can point to its classical equivalent.
- Synonyms (Sanskrit, English, Hindi, Gujarati names) make searching easy.
- Every change is kept in MedicineVersion, so old prescriptions keep exactly what was prescribed.
- Each branch can change the price and switch a medicine off (BranchMedicine).
- Medicines are never deleted; switch them off instead.
"""
from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.common.models import BranchScopedModel, OrgScopedModel

KIND_CHOICES = [("classical", "Classical"), ("proprietary", "Patent & Proprietary")]


class Medicine(OrgScopedModel):
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default="classical", db_index=True)
    name = models.CharField("Name (official name or brand)", max_length=200)
    name_gu = models.CharField("Name (Gujarati)", max_length=200, blank=True)
    name_hi = models.CharField("Name (Hindi)", max_length=200, blank=True)
    synonyms = models.TextField(blank=True, help_text="Other names, comma separated (Sanskrit, English, Hindi, Gujarati)")
    generic_name = models.CharField(max_length=200, blank=True, help_text="e.g. the classical name or main ingredient")
    category = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    dosage_form = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    composition = models.TextField(blank=True)
    reference = models.CharField("Reference (AFI / API)", max_length=300, blank=True)
    manufacturer = models.CharField(max_length=200, blank=True)
    classical_equivalent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="brands",
        limit_choices_to={"kind": "classical"},
    )
    ayush_licence_no = models.CharField("Ayush licence no.", max_length=60, blank=True)
    hsn_code = models.CharField("HSN code", max_length=10, blank=True)
    gst_rate = models.DecimalField("GST %", max_digits=5, decimal_places=2, default=12)
    mrp = models.DecimalField("Price (MRP)", max_digits=10, decimal_places=2, null=True, blank=True)
    pack_size = models.CharField(max_length=60, blank=True)  # e.g. "100 g", "60 tablets", "450 ml"
    pack_type = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    # Loose selling: stock is counted in packs; with allow_loose the pharmacy may give part of a pack
    units_per_pack = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # e.g. 60 (tablets)
    allow_loose = models.BooleanField("Can be sold loose", default=False)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                        help_text="Usual selling price per pack (MRP is the maximum)")
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    strength = models.CharField(max_length=60, blank=True)  # e.g. "500 mg", "10 mg/ml"
    sku = models.CharField("Medicine code (SKU)", max_length=40, blank=True)  # the clinic's own short code
    notes = models.TextField(blank=True)

    # What the prescription screen fills in by default
    default_dose = models.CharField(max_length=20, blank=True)  # e.g. "2", "3-5"
    dose_unit = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    default_frequency = models.CharField(max_length=20, blank=True)  # e.g. "1-0-1"
    default_timing = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    default_anupana = models.ForeignKey("common.MasterValue", null=True, blank=True, on_delete=models.PROTECT, related_name="+")

    # Safety flags: the prescription screen shows fixed warnings for these (see prescriptions/safety.py)
    schedule_e1 = models.BooleanField("Schedule E1", default=False)
    contains_metals = models.BooleanField("Contains metals / bhasma", default=False)
    pregnancy_caution = models.BooleanField(default=False)
    child_caution = models.BooleanField(default=False)
    safety_notes = models.CharField(max_length=300, blank=True)

    is_sample = models.BooleanField(default=False, help_text="Sample entry - pharmacist to verify")
    is_active = models.BooleanField(default=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "kind", "name"], condition=Q(is_deleted=False),
                                    name="uniq_medicine_name_per_kind"),
            models.UniqueConstraint(fields=["organization", "barcode"], condition=Q(is_deleted=False) & ~Q(barcode=""),
                                    name="uniq_medicine_barcode"),
            models.UniqueConstraint(fields=["organization", "sku"], condition=Q(is_deleted=False) & ~Q(sku=""),
                                    name="uniq_medicine_sku"),
        ]
        indexes = [models.Index(fields=["organization", "is_active"])]

    def __str__(self):
        return self.name


class MedicineVersion(models.Model):
    """A frozen copy of a medicine's details, saved on every change."""

    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")

    class Meta:
        ordering = ["medicine", "-version"]
        constraints = [models.UniqueConstraint(fields=["medicine", "version"], name="uniq_medicine_version")]


class BranchMedicine(BranchScopedModel):
    """A branch's own price, whether the medicine is used there, and its low-stock level."""

    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name="branch_settings")
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    # Pharmacy: warn "low stock" when the branch has this many packs or fewer
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch", "medicine"], condition=Q(is_deleted=False),
                                    name="uniq_branch_medicine"),
        ]
