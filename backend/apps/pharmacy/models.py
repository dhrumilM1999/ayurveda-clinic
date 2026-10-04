"""
Pharmacy: racks, stock by batch, purchases, returns, sales (dispensing), physical stock checks, stock ledger.
ASK FIRST before changing these models (it changes the database).

- Stock belongs to a BRANCH and is kept per BATCH (same medicine, different batch = different expiry,
  purchase price, MRP). Quantities are counted in packs (e.g. 1 bottle); a loose sale is a part of a pack.
- Every stock change writes one StockMovement line (the stock ledger). The ledger is never edited.
- Nothing is ever deleted.
"""
from django.db import models
from django.db.models import Q

from apps.common.models import BranchScopedModel, OrgScopedModel

QTY = {"max_digits": 12, "decimal_places": 3}
MONEY = {"max_digits": 12, "decimal_places": 2}
RATE = {"max_digits": 5, "decimal_places": 2}


# --- Where things are kept ------------------------------------------------------------------
class Rack(BranchScopedModel):
    """A rack / cupboard in the pharmacy, e.g. "A" (Churna) with shelves 1-5."""

    code = models.CharField(max_length=20)  # e.g. "A"
    name = models.CharField(max_length=100, blank=True)  # e.g. "Churna and powders"
    shelves = models.PositiveSmallIntegerField(default=5)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "code"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "code"], condition=Q(is_deleted=False), name="uniq_rack_code"),
        ]

    def __str__(self):
        return self.code


class ProductLocation(BranchScopedModel):
    """Where a medicine is kept in this branch: rack + shelf (+ optional box / bin)."""

    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="locations")
    rack = models.ForeignKey(Rack, null=True, blank=True, on_delete=models.PROTECT, related_name="products")
    shelf = models.CharField(max_length=20, blank=True)  # e.g. "3"
    bin = models.CharField(max_length=20, blank=True)  # e.g. "Box 12"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch", "medicine"], condition=Q(is_deleted=False), name="uniq_product_location"),
        ]

    @property
    def label(self) -> str:
        parts = [self.rack.code if self.rack_id else "", self.shelf, self.bin]
        return "-".join(p for p in parts if p)


class Supplier(OrgScopedModel):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    gstin = models.CharField("GSTIN", max_length=15, blank=True)
    drug_licence_no = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    state = models.CharField(max_length=100, blank=True)
    payment_terms_days = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# --- Stock ------------------------------------------------------------------------------------
class StockBatch(BranchScopedModel):
    """One batch of one medicine in one branch (e.g. Triphala Churna, batch TC2401, expires 06-2027)."""

    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="batches")
    batch_no = models.CharField(max_length=60)
    mfg_date = models.DateField("Manufactured", null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    mrp = models.DecimalField("MRP per pack", **MONEY)
    selling_price = models.DecimalField("Selling price per pack (with GST)", null=True, blank=True, **MONEY)
    purchase_rate = models.DecimalField("Purchase price per pack (without GST)", null=True, blank=True, **MONEY)
    gst_rate = models.DecimalField(default=12, **RATE)
    barcode = models.CharField(max_length=64, blank=True, db_index=True)
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField("Available (packs)", default=0, **QTY)

    class Meta:
        ordering = ["expiry_date", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "medicine", "batch_no"], condition=Q(is_deleted=False),
                                    name="uniq_stock_batch"),
            models.CheckConstraint(condition=Q(quantity__gte=0), name="stock_not_negative"),
        ]

    def __str__(self):
        return f"{self.medicine.name} / {self.batch_no}"

    @property
    def sale_price(self):
        """Price per pack used when selling: the selling price, else the MRP."""
        return self.selling_price if self.selling_price is not None else self.mrp


# --- Purchases ------------------------------------------------------------------------------
class Purchase(BranchScopedModel):
    """Medicines received from a supplier (one supplier invoice), or OPENING stock (is_opening)."""

    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name="purchases")
    invoice_no = models.CharField(max_length=60, blank=True)
    invoice_date = models.DateField(db_index=True)
    is_opening = models.BooleanField(default=False)
    taxable_amount = models.DecimalField(default=0, **MONEY)
    discount_amount = models.DecimalField(default=0, **MONEY)
    gst_amount = models.DecimalField(default=0, **MONEY)
    other_charges = models.DecimalField(default=0, **MONEY)
    round_off = models.DecimalField(default=0, **MONEY)
    total_amount = models.DecimalField(default=0, **MONEY)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-invoice_date", "-created_at"]


class PurchaseItem(OrgScopedModel):
    purchase = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name="items")
    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="purchase_items")
    quantity = models.DecimalField("Paid quantity (packs)", **QTY)
    free_quantity = models.DecimalField(default=0, **QTY)
    purchase_rate = models.DecimalField(null=True, blank=True, **MONEY)  # per pack, without GST
    discount_percent = models.DecimalField(default=0, **RATE)
    gst_rate = models.DecimalField(default=12, **RATE)
    mrp = models.DecimalField(**MONEY)
    selling_price = models.DecimalField(null=True, blank=True, **MONEY)
    taxable_amount = models.DecimalField(default=0, **MONEY)
    gst_amount = models.DecimalField(default=0, **MONEY)
    amount = models.DecimalField(default=0, **MONEY)  # taxable + GST


class PurchaseReturn(BranchScopedModel):
    """Medicines sent back to the supplier (e.g. damaged, near expiry). Stock goes down."""

    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name="returns")
    return_date = models.DateField(db_index=True)
    reference = models.CharField(max_length=60, blank=True)  # supplier credit note / debit note no.
    reason = models.CharField(max_length=200)
    total_amount = models.DecimalField(default=0, **MONEY)

    class Meta:
        ordering = ["-return_date", "-created_at"]


class PurchaseReturnItem(OrgScopedModel):
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.PROTECT, related_name="items")
    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(**QTY)
    rate = models.DecimalField(**MONEY)
    amount = models.DecimalField(**MONEY)


# --- Sales (dispensing) ----------------------------------------------------------------------
class Dispense(BranchScopedModel):
    """Medicines given to a patient against a prescription. A bill (billing.Invoice) is made for it."""

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
    quantity = models.DecimalField("Packs", **QTY)
    loose_units = models.DecimalField(null=True, blank=True, **QTY)  # e.g. 20 tablets (shown on the bill)
    mrp = models.DecimalField("Price per pack", **MONEY)
    discount_percent = models.DecimalField(default=0, **RATE)
    amount = models.DecimalField(**MONEY)
    returned_quantity = models.DecimalField(default=0, **QTY)


class SaleReturn(BranchScopedModel):
    """Medicines brought back by the patient. Stock goes up; a credit note is made on the bill."""

    dispense = models.ForeignKey(Dispense, on_delete=models.PROTECT, related_name="returns")
    patient = models.ForeignKey("patients.Patient", on_delete=models.PROTECT, related_name="+")
    reason = models.CharField(max_length=200)
    total_amount = models.DecimalField(default=0, **MONEY)

    class Meta:
        ordering = ["-created_at"]


class SaleReturnItem(OrgScopedModel):
    sale_return = models.ForeignKey(SaleReturn, on_delete=models.PROTECT, related_name="items")
    dispense_item = models.ForeignKey(DispenseItem, on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(**QTY)
    amount = models.DecimalField(**MONEY)
    back_to_stock = models.BooleanField(default=True)  # False = damaged, not sellable


# --- Physical stock check ----------------------------------------------------------------------
class StockVerification(BranchScopedModel):
    """A physical count of the shelves. On completion, differences are posted to the ledger."""

    STATUS = [("open", "Counting"), ("completed", "Completed")]
    title = models.CharField(max_length=120)
    rack = models.ForeignKey(Rack, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=10, choices=STATUS, default="open")
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]


class StockVerificationItem(OrgScopedModel):
    verification = models.ForeignKey(StockVerification, on_delete=models.PROTECT, related_name="items")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="+")
    system_quantity = models.DecimalField(**QTY)
    counted_quantity = models.DecimalField(null=True, blank=True, **QTY)

    class Meta:
        ordering = ["batch__medicine__name", "batch__expiry_date"]


# --- Stock ledger ----------------------------------------------------------------------------
MOVEMENT_KINDS = [
    ("opening", "Opening stock"),
    ("purchase", "Purchase"),
    ("free", "Free quantity"),
    ("dispense", "Sale"),
    ("sale_return", "Sale return"),
    ("purchase_return", "Purchase return"),
    ("damaged", "Damaged"),
    ("expired", "Expired - removed"),
    ("adjust", "Manual correction"),
    ("verification", "Physical count difference"),
]


class StockMovement(BranchScopedModel):
    """One change of stock (+ in, - out). Together these lines are the stock ledger of every batch."""

    medicine = models.ForeignKey("medicines.Medicine", on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey(StockBatch, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=20, choices=MOVEMENT_KINDS, db_index=True)
    quantity = models.DecimalField(**QTY)  # + in, - out
    balance_after = models.DecimalField(**QTY)
    reason = models.CharField(max_length=200, blank=True)
    reference = models.CharField(max_length=64, blank=True)  # id of the purchase / sale / return / check
    reference_label = models.CharField(max_length=100, blank=True)  # e.g. invoice no. shown in the ledger

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["branch", "medicine", "created_at"])]
