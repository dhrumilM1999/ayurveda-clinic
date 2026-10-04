"""
Bills (invoices), payments and credit notes. ASK FIRST before changing these models.

Rules (CLAUDE.md section 9):
- Invoice numbers are per BRANCH, per SERIES (PH = pharmacy, OP = clinic) and per FINANCIAL YEAR (April-March),
  sequential and never duplicated (made inside a database transaction).
- Prices are GST-INCLUSIVE (like MRP). The bill shows taxable value + CGST + SGST (same state).
- Cancelling or returning creates a CREDIT NOTE. Invoices are never deleted or changed after payment.
- Payment modes: cash, UPI, card.
"""
from django.db import models

from apps.common.models import BranchScopedModel, OrgScopedModel

MONEY = {"max_digits": 12, "decimal_places": 2}
QTY = {"max_digits": 12, "decimal_places": 3}
RATE = {"max_digits": 5, "decimal_places": 2}

SERIES = [("PH", "Pharmacy"), ("OP", "Clinic (consultation, therapy)")]
PAYMENT_MODES = [("cash", "Cash"), ("upi", "UPI"), ("card", "Card")]
LINE_KINDS = [("medicine", "Medicine"), ("consultation", "Consultation"), ("therapy", "Therapy"), ("other", "Other")]
STATUSES = [("unpaid", "Not paid"), ("partly_paid", "Partly paid"), ("paid", "Paid"), ("cancelled", "Cancelled")]


class DocumentSequence(models.Model):
    """Running number per branch, per series, per financial year (e.g. PH 2026-27)."""

    branch = models.ForeignKey("organizations.Branch", on_delete=models.PROTECT, related_name="+")
    series = models.CharField(max_length=10)
    financial_year = models.CharField(max_length=7)  # "2026-27"
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["branch", "series", "financial_year"], name="uniq_document_sequence"),
        ]


class Invoice(BranchScopedModel):
    number = models.CharField(max_length=40)
    series = models.CharField(max_length=10, choices=SERIES, default="PH")
    financial_year = models.CharField(max_length=7)
    invoice_date = models.DateField(db_index=True)
    patient = models.ForeignKey("patients.Patient", null=True, blank=True, on_delete=models.PROTECT, related_name="invoices")
    prescription = models.ForeignKey("prescriptions.Prescription", null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="invoices")
    dispense = models.OneToOneField("pharmacy.Dispense", null=True, blank=True, on_delete=models.PROTECT,
                                    related_name="invoice")
    customer_name = models.CharField(max_length=200, blank=True)  # copy, as printed
    place_of_supply = models.CharField(max_length=100, blank=True)  # state

    gross_amount = models.DecimalField(default=0, **MONEY)  # before discount
    discount_amount = models.DecimalField(default=0, **MONEY)
    taxable_amount = models.DecimalField(default=0, **MONEY)
    cgst_amount = models.DecimalField(default=0, **MONEY)
    sgst_amount = models.DecimalField(default=0, **MONEY)
    igst_amount = models.DecimalField(default=0, **MONEY)
    round_off = models.DecimalField(default=0, **MONEY)
    total_amount = models.DecimalField(default=0, **MONEY)
    paid_amount = models.DecimalField(default=0, **MONEY)
    credited_amount = models.DecimalField(default=0, **MONEY)  # reduced by credit notes
    refunded_amount = models.DecimalField(default=0, **MONEY)  # money given back

    status = models.CharField(max_length=12, choices=STATUSES, default="unpaid", db_index=True)
    notes = models.CharField(max_length=300, blank=True)
    print_count = models.PositiveIntegerField(default=0)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-invoice_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "number"], name="uniq_invoice_number_per_branch"),
        ]
        indexes = [models.Index(fields=["branch", "invoice_date"])]

    def __str__(self):
        return self.number

    @property
    def balance(self):
        """Still to be paid (negative = clinic owes the patient money back)."""
        return self.total_amount - self.credited_amount - (self.paid_amount - self.refunded_amount)


class InvoiceLine(OrgScopedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="lines")
    kind = models.CharField(max_length=20, choices=LINE_KINDS, default="medicine")
    description = models.CharField(max_length=250)
    medicine = models.ForeignKey("medicines.Medicine", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    batch = models.ForeignKey("pharmacy.StockBatch", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    dispense_item = models.ForeignKey("pharmacy.DispenseItem", null=True, blank=True, on_delete=models.PROTECT,
                                      related_name="invoice_lines")
    batch_no = models.CharField(max_length=60, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    hsn_code = models.CharField(max_length=10, blank=True)
    quantity = models.DecimalField(**QTY)
    unit_label = models.CharField(max_length=40, blank=True)  # e.g. "bottle", "20 tablets"
    unit_price = models.DecimalField(**MONEY)  # with GST
    discount_percent = models.DecimalField(default=0, **RATE)
    gross_amount = models.DecimalField(**MONEY)
    discount_amount = models.DecimalField(default=0, **MONEY)
    gst_rate = models.DecimalField(default=0, **RATE)
    taxable_amount = models.DecimalField(**MONEY)
    cgst_amount = models.DecimalField(default=0, **MONEY)
    sgst_amount = models.DecimalField(default=0, **MONEY)
    total_amount = models.DecimalField(**MONEY)
    credited_quantity = models.DecimalField(default=0, **QTY)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "created_at"]


class Payment(BranchScopedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    mode = models.CharField(max_length=10, choices=PAYMENT_MODES)
    amount = models.DecimalField(**MONEY)
    reference = models.CharField(max_length=100, blank=True)  # UPI ref / card slip no.
    paid_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["paid_at"]


class CreditNote(BranchScopedModel):
    """Money given back / reduced on a bill (return or cancellation). Never deleted."""

    number = models.CharField(max_length=40)
    financial_year = models.CharField(max_length=7)
    note_date = models.DateField(db_index=True)
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="credit_notes")
    sale_return = models.OneToOneField("pharmacy.SaleReturn", null=True, blank=True, on_delete=models.PROTECT,
                                       related_name="credit_note")
    reason = models.CharField(max_length=200)
    taxable_amount = models.DecimalField(default=0, **MONEY)
    cgst_amount = models.DecimalField(default=0, **MONEY)
    sgst_amount = models.DecimalField(default=0, **MONEY)
    total_amount = models.DecimalField(default=0, **MONEY)
    refund_mode = models.CharField(max_length=10, choices=PAYMENT_MODES + [("none", "No refund (bill not paid)")],
                                   default="cash")
    refund_amount = models.DecimalField(default=0, **MONEY)

    class Meta:
        ordering = ["-note_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["branch", "number"], name="uniq_credit_note_number_per_branch"),
        ]


class CreditNoteLine(OrgScopedModel):
    credit_note = models.ForeignKey(CreditNote, on_delete=models.PROTECT, related_name="lines")
    invoice_line = models.ForeignKey(InvoiceLine, on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(**QTY)
    taxable_amount = models.DecimalField(**MONEY)
    cgst_amount = models.DecimalField(default=0, **MONEY)
    sgst_amount = models.DecimalField(default=0, **MONEY)
    total_amount = models.DecimalField(**MONEY)

