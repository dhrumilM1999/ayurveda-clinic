"""
Pharmacy rules: receiving stock, dispensing from prescriptions (earliest expiry first), corrections, stock summary.
All stock changes lock the batch row and write a StockMovement, so two people can't sell the same last pack.
"""
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import DecimalField, Min, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.medicines.models import BranchMedicine, Medicine

from .models import Dispense, DispenseItem, Purchase, PurchaseItem, StockBatch, StockMovement

EXPIRY_WARNING_DAYS = 90  # SAFE TO EDIT: "expiring soon" means within this many days
ZERO = Decimal("0")
PAISA = Decimal("0.01")


def rupees(value: Decimal) -> Decimal:
    """Round to 2 decimals (paise)."""
    return value.quantize(PAISA)


def _move(batch, kind, quantity, user, reason="", reference=""):
    StockMovement.objects.create(
        organization_id=batch.organization_id, branch_id=batch.branch_id, medicine_id=batch.medicine_id, batch=batch,
        kind=kind, quantity=quantity, balance_after=batch.quantity, reason=reason[:200], reference=str(reference)[:64],
        created_by=user, updated_by=user,
    )


# --- Stock in ----------------------------------------------------------------------
@transaction.atomic
def receive_purchase(branch, user, *, supplier, invoice_no, invoice_date, notes, items) -> Purchase:
    """
    items: [{"medicine": Medicine, "batch_no", "expiry_date", "quantity", "purchase_rate", "mrp"}]
    A batch number already in stock gets the quantity added (and the new price / expiry).
    """
    purchase = Purchase.objects.create(
        organization_id=branch.organization_id, branch=branch, supplier=supplier, invoice_no=invoice_no,
        invoice_date=invoice_date, notes=notes, created_by=user, updated_by=user,
    )
    total = ZERO
    for item in items:
        medicine: Medicine = item["medicine"]
        batch = (StockBatch.objects.select_for_update()
                 .filter(branch=branch, medicine=medicine, batch_no=item["batch_no"]).first())
        if batch is None:
            batch = StockBatch(organization_id=branch.organization_id, branch=branch, medicine=medicine,
                               batch_no=item["batch_no"], mrp=item["mrp"], created_by=user)
        batch.expiry_date = item.get("expiry_date") or batch.expiry_date
        batch.mrp = item["mrp"]
        if item.get("purchase_rate") is not None:
            batch.purchase_rate = item["purchase_rate"]
        batch.quantity = (batch.quantity or ZERO) + item["quantity"]
        batch.updated_by = user
        batch.save()
        amount = rupees((item.get("purchase_rate") or ZERO) * item["quantity"])
        PurchaseItem.objects.create(
            organization_id=branch.organization_id, purchase=purchase, medicine=medicine, batch=batch,
            quantity=item["quantity"], purchase_rate=item.get("purchase_rate"), mrp=item["mrp"], amount=amount,
            created_by=user, updated_by=user,
        )
        _move(batch, "purchase", item["quantity"], user, reason=f"Invoice {invoice_no}".strip(), reference=purchase.id)
        total += amount
    purchase.total_amount = total
    purchase.save(update_fields=["total_amount"])
    return purchase


# --- Corrections ---------------------------------------------------------------------
@transaction.atomic
def adjust_stock(batch_id, branch, change: Decimal, reason: str, user) -> StockBatch:
    """+/- correction (damaged, expired thrown away, counting error). A reason is required."""
    if not reason.strip():
        raise ValidationError({"reason": "Please write why the stock is corrected."})
    batch = StockBatch.objects.select_for_update().filter(branch=branch, pk=batch_id).first()
    if batch is None:
        raise ValidationError({"batch": "Batch not found in this branch."})
    if batch.quantity + change < 0:
        raise ValidationError({"quantity": f"Only {batch.quantity} available."})
    batch.quantity += change
    batch.updated_by = user
    batch.save(update_fields=["quantity", "updated_by", "updated_at"])
    _move(batch, "adjust", change, user, reason=reason)
    return batch


# --- Dispensing ------------------------------------------------------------------------
def suggested_batches(branch, medicine_ids) -> dict:
    """{medicine_id: [batches with stock, not expired, earliest expiry first]} (FEFO)."""
    today = timezone.localdate()
    batches = (StockBatch.objects.filter(branch=branch, medicine_id__in=medicine_ids, quantity__gt=0)
               .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
               .order_by("expiry_date", "created_at"))
    result = {}
    for b in batches:
        result.setdefault(b.medicine_id, []).append(b)
    return result


def dispensed_quantities(prescription) -> dict:
    """{prescription_item_id: quantity already given}"""
    rows = (DispenseItem.objects.filter(dispense__prescription=prescription, prescription_item__isnull=False)
            .values("prescription_item_id").annotate(total=Sum("quantity")))
    return {r["prescription_item_id"]: r["total"] for r in rows}


def dispense_status(prescription) -> str:
    """'pending' (nothing given), 'partly', or 'done' (every stock medicine given at least once)."""
    stock_items = [i for i in prescription.items.all() if i.medicine_id]
    if not stock_items:
        return "pending"
    given = dispensed_quantities(prescription)
    count = sum(1 for i in stock_items if given.get(i.id))
    return "pending" if count == 0 else ("done" if count == len(stock_items) else "partly")


@transaction.atomic
def dispense(prescription, branch, user, lines: list[dict], notes: str = "") -> Dispense:
    """
    lines: [{"prescription_item": PrescriptionItem, "batch_id": uuid, "quantity": Decimal}]
    Checks: final prescription of this branch, batch of the same medicine, not expired, enough stock.
    """
    if prescription.branch_id != branch.id:
        raise ValidationError({"detail": "This prescription belongs to another branch."})
    if prescription.status != "final":
        raise ValidationError({"detail": "The doctor has not completed this prescription yet."})
    if not lines:
        raise ValidationError({"items": "Choose at least one medicine to give."})
    today = timezone.localdate()
    record = Dispense.objects.create(
        organization_id=branch.organization_id, branch=branch, prescription=prescription,
        patient_id=prescription.patient_id, notes=notes[:300], created_by=user, updated_by=user,
    )
    total = ZERO
    for line in lines:
        item = line["prescription_item"]
        if item.prescription_id != prescription.id or not item.medicine_id:
            raise ValidationError({"items": "A line does not belong to this prescription."})
        quantity = line["quantity"]
        if quantity <= 0:
            raise ValidationError({"items": f"{item.medicine_name}: quantity must be more than 0."})
        batch = StockBatch.objects.select_for_update().filter(branch=branch, pk=line["batch_id"]).first()
        if batch is None or batch.medicine_id != item.medicine_id:
            raise ValidationError({"items": f"{item.medicine_name}: choose a batch of this medicine."})
        if batch.expiry_date and batch.expiry_date < today:
            raise ValidationError({"items": f"{item.medicine_name}: batch {batch.batch_no} has expired."})
        if batch.quantity < quantity:
            raise ValidationError({"items": f"{item.medicine_name}: only {batch.quantity} left in batch {batch.batch_no}."})
        batch.quantity -= quantity
        batch.updated_by = user
        batch.save(update_fields=["quantity", "updated_by", "updated_at"])
        amount = rupees(batch.mrp * quantity)
        DispenseItem.objects.create(
            organization_id=branch.organization_id, dispense=record, prescription_item=item, medicine_id=item.medicine_id,
            batch=batch, quantity=quantity, mrp=batch.mrp, amount=amount, created_by=user, updated_by=user,
        )
        _move(batch, "dispense", -quantity, user, reason=f"Rx of {prescription.patient.full_name}", reference=record.id)
        total += amount
    record.total_amount = total
    record.save(update_fields=["total_amount"])
    return record


# --- Stock summary -------------------------------------------------------------------------
def stock_summary(branch, search="", show="all"):
    """
    One row per medicine that has ever been in stock in this branch (plus low-stock levels):
    available, nearest expiry, reorder level, flags low / expiring / expired.
    show: all | low | expiring | expired
    """
    today = timezone.localdate()
    soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
    dec = DecimalField(max_digits=10, decimal_places=2)
    # First pick the medicines, then add up their stock (separate steps, so totals are never counted twice)
    with_stock = StockBatch.objects.filter(branch=branch).values("medicine_id")
    with_level = BranchMedicine.objects.filter(branch=branch, reorder_level__isnull=False).values("medicine_id")
    medicines = Medicine.objects.filter(organization_id=branch.organization_id).filter(
        Q(id__in=with_stock) | Q(id__in=with_level)
    )
    if search:
        from apps.medicines.services import search_filter

        medicines = medicines.filter(search_filter(search))
    in_branch = Q(batches__branch=branch, batches__is_deleted=False)
    medicines = medicines.annotate(
        available=Coalesce(Sum("batches__quantity", filter=in_branch & Q(batches__quantity__gt=0)), Value(ZERO), output_field=dec),
        usable=Coalesce(Sum("batches__quantity", filter=in_branch & Q(batches__quantity__gt=0)
                            & (Q(batches__expiry_date__isnull=True) | Q(batches__expiry_date__gte=today))),
                        Value(ZERO), output_field=dec),
        nearest_expiry=Min("batches__expiry_date", filter=in_branch & Q(batches__quantity__gt=0)),
    ).order_by("name")
    levels = dict(BranchMedicine.objects.filter(branch=branch).values_list("medicine_id", "reorder_level"))
    rows = []
    for m in medicines:
        level = levels.get(m.id)
        row = {
            "medicine": m, "available": m.available, "usable": m.usable, "nearest_expiry": m.nearest_expiry,
            "reorder_level": level,
            "low": level is not None and m.usable <= level,
            "expired": m.available > m.usable,
            "expiring": bool(m.nearest_expiry and today <= m.nearest_expiry <= soon),
        }
        if show == "low" and not row["low"]:
            continue
        if show == "expiring" and not row["expiring"]:
            continue
        if show == "expired" and not row["expired"]:
            continue
        rows.append(row)
    return rows


def set_reorder_level(medicine, branch, level, user):
    row = BranchMedicine.objects.filter(branch=branch, medicine=medicine).first()
    if row is None:
        row = BranchMedicine(organization_id=medicine.organization_id, branch=branch, medicine=medicine, created_by=user)
    row.reorder_level = level
    row.updated_by = user
    row.save()
    return row
