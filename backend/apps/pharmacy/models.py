"""
Pharmacy: stock by batch, purchases (stock in), dispensing from prescriptions (stock out), stock history.
ASK FIRST before changing these models (it changes the database).

- Stock belongs to a BRANCH. Quantities are counted in packs / units of sale (bottle, box, strip...).
- Every stock change writes a StockMovement line, so the stock history can always be checked.
- Nothing is ever deleted.
"""
from django.db import models
from django.db.models import Q

from apps.common.models import BranchScopedModel, OrgScopedModel

QTY = {"max_digits": 10, "decimal_places": 2}
MONEY = {"max_digits": 12, "decimal_places": 2}


class Supplier(OrgScopedModel):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class StockBatch(BranchScopedModel):
    """One batch of one medicine in one branch (e.g. Triphala Churna, batch TC2401, expires 06-2027)."""

    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="batches")
    batch_no = models.CharField(max_length=60)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    mrp = models.DecimalField("Sale price (MRP)", **MONEY)
    purchase_rate = models.DecimalField(null=True, blank=True, **MONEY)
    quantity = models.DecimalField("Available", default=0, **QTY)

    class Meta:
        ordering = ["expiry_date", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "medicine", "batch_no"], condition=Q(is_deleted=False),
                                    name="uniq_stock_batch"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_not_negative"),
        ]

    def __str__(self):
        return f"{self.medicine.name} / {self.batch_no}"


class Purchase(BranchScopedModel):
    """Medicines received from a supplier (one supplier invoice)."""

    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name="purchases")
    invoice_no = models.CharField(max_length=60, blank=True)
    invoice_date = models.DateField(db_index=True)
    total_amount = models.DecimalField(default=0, **MONEY)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-invoice_date", "-created_at"]


class PurchaseItem(OrgScopedModel):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="items")
    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(**QTY)
    purchase_rate = models.DecimalField(null=True, blank=True, **MONEY)
    mrp = models.DecimalField(**MONEY)
    amount = models.DecimalField(default=0, **MONEY)


class Dispense(BranchScopedModel):
    """Medicines handed over to a patient against a prescription."""

    prescription = models.ForeignKey("prescriptions.Prescription", on_delete=models.PROTECT, related_name="dispenses")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="dispenses")
    total_amount = models.DecimalField(default=0, **MONEY)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]


class DispenseItem(OrgScopedModel):
    dispense = models.ForeignKey(Dispense, on_delete=models.PROTECT, related_name="items")
    prescription_item = models.ForeignKey("prescriptions.PrescriptionItem", null=True, blank=True,
                                          on_delete=models.PROTECT, related_name="dispensed")
    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(**QTY)
    mrp = models.DecimalField(**MONEY)
    amount = models.DecimalField(**MONEY)


MOVEMENT_KINDS = [
    ("purchase", "Received (purchase)"),
    ("dispense", "Given to patient"),
    ("adjust", "Correction"),
]


class StockMovement(BranchScopedModel):
    """One change of stock: + received, - given, +/- correction. The stock history of every batch."""

    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=20, choices=MOVEMENT_KINDS, db_index=True)
    quantity = models.DecimalField(**QTY)  # + in, - out
    balance_after = models.DecimalField(**QTY)
    reason = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=64, blank=True)  # id of the purchase / dispense

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["branch", "medicine", "created_at"])]
