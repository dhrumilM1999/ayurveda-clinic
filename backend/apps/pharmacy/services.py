"""
Pharmacy rules. Every stock change locks the batch row (two people can't sell the same last pack) and writes a
StockMovement line (the stock ledger).

  receive_stock     purchase invoice or opening stock (+ free quantity)
  return_to_supplier purchase return
  sell              dispense a prescription -> stock out + bill (billing app)
  take_back         sale return -> stock in (unless damaged) + credit note
  correct_stock     damaged / expired / manual correction
  physical count    start_verification -> save counts -> complete_verification
"""
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.billing.services import create_credit_note, create_invoice, invoice_for_dispense, record_payment
from apps.medicines.models import BranchMedicine, Medicine

from .models import (
    Dispense, DispenseItem, ProductLocation, Purchase, PurchaseItem, PurchaseReturn, PurchaseReturnItem,
    SaleReturn, SaleReturnItem, StockBatch, StockMovement, StockVerification, StockVerificationItem,
)

EXPIRY_WARNING_DAYS = 90  # SAFE TO EDIT: "near expiry" means within this many days
ZERO = Decimal("0")
PAISA = Decimal("0.01")
RUPEE = Decimal("1")


def rupees(value) -> Decimal:
    return Decimal(value).quantize(PAISA, rounding=ROUND_HALF_UP)


def _move(batch, kind, quantity, user, reason="", reference="", label=""):
    StockMovement.objects.create(
        organization_id=batch.organization_id, branch_id=batch.branch_id, medicine_id=batch.medicine_id, batch=batch,
        kind=kind, quantity=quantity, balance_after=batch.quantity, reason=str(reason)[:200],
        reference=str(reference)[:64], reference_label=str(label)[:100], created_by=user, updated_by=user,
    )


def _locked_batch(branch, batch_id) -> StockBatch:
    batch = StockBatch.objects.select_for_update().select_related("medicine").filter(branch=branch, pk=batch_id).first()
    if batch is None:
        raise ValidationError({"batch": "Batch not found in this branch."})
    return batch


# --- Stock in: purchase invoice / opening stock -----------------------------------------------
@transaction.atomic
def receive_stock(branch, user, *, items, supplier=None, invoice_no="", invoice_date=None, notes="",
                  other_charges=ZERO, is_opening=False) -> Purchase:
    """
    items: [{"medicine", "batch_no", "mfg_date", "expiry_date", "quantity", "free_quantity", "purchase_rate",
             "discount_percent", "gst_rate", "mrp", "selling_price", "barcode"}]
    A batch number already in stock gets the quantity added (and the latest prices / dates).
    """
    today = timezone.localdate()
    purchase = Purchase.objects.create(
        organization_id=branch.organization_id, branch=branch, supplier=supplier, invoice_no=invoice_no,
        invoice_date=invoice_date or today, is_opening=is_opening, notes=notes[:300], other_charges=other_charges,
        created_by=user, updated_by=user,
    )
    if is_opening:
        label = "Opening stock"
    elif invoice_no:
        label = f"Invoice {invoice_no}"
    else:
        label = f"Purchase from {supplier.name}" if supplier else "Purchase (no invoice no.)"
    totals = {"taxable": ZERO, "discount": ZERO, "gst": ZERO}
    for item in items:
        medicine: Medicine = item["medicine"]
        if item.get("expiry_date") and item["expiry_date"] < today:
            raise ValidationError({"items": f"{medicine.name}: batch {item['batch_no']} has already expired."})
        if item.get("mfg_date") and item.get("expiry_date") and item["mfg_date"] >= item["expiry_date"]:
            raise ValidationError({"items": f"{medicine.name}: manufacturing date must be before expiry."})
        if item.get("selling_price") is not None and item["selling_price"] > item["mrp"]:
            raise ValidationError({"items": f"{medicine.name}: selling price cannot be more than MRP."})
        quantity, free = item["quantity"], item.get("free_quantity") or ZERO
        batch = (StockBatch.objects.select_for_update()
                 .filter(branch=branch, medicine=medicine, batch_no=item["batch_no"]).first())
        if batch is None:
            batch = StockBatch(organization_id=branch.organization_id, branch=branch, medicine=medicine,
                               batch_no=item["batch_no"], mrp=item["mrp"], created_by=user)
        for field in ("mfg_date", "expiry_date", "selling_price", "barcode"):
            if item.get(field):
                setattr(batch, field, item[field])
        batch.mrp = item["mrp"]
        batch.gst_rate = item.get("gst_rate", medicine.gst_rate)
        if item.get("purchase_rate") is not None:
            batch.purchase_rate = item["purchase_rate"]
        if supplier is not None:
            batch.supplier = supplier
        batch.quantity = (batch.quantity or ZERO) + quantity + free
        batch.updated_by = user
        batch.save()

        rate = item.get("purchase_rate") or ZERO
        gross = rupees(rate * quantity)
        discount = rupees(gross * Decimal(item.get("discount_percent") or 0) / 100)
        taxable = gross - discount
        gst = rupees(taxable * Decimal(batch.gst_rate) / 100)
        PurchaseItem.objects.create(
            organization_id=branch.organization_id, purchase=purchase, medicine=medicine, batch=batch,
            quantity=quantity, free_quantity=free, purchase_rate=item.get("purchase_rate"),
            discount_percent=item.get("discount_percent") or 0, gst_rate=batch.gst_rate, mrp=item["mrp"],
            selling_price=item.get("selling_price"), taxable_amount=taxable, gst_amount=gst, amount=taxable + gst,
            created_by=user, updated_by=user,
        )
        # Ledger: paid quantity and free quantity as separate lines (balance shown after each)
        batch.quantity -= free
        _move(batch, "opening" if is_opening else "purchase", quantity, user, reference=purchase.id, label=label)
        if free:
            batch.quantity += free
            _move(batch, "free", free, user, reason="Free quantity from supplier", reference=purchase.id, label=label)
        totals["taxable"] += taxable
        totals["discount"] += discount
        totals["gst"] += gst
    exact = totals["taxable"] + totals["gst"] + Decimal(other_charges or 0)
    total = exact.quantize(RUPEE, rounding=ROUND_HALF_UP).quantize(PAISA)
    purchase.taxable_amount, purchase.discount_amount, purchase.gst_amount = totals["taxable"], totals["discount"], totals["gst"]
    purchase.round_off = total - exact
    purchase.total_amount = total
    purchase.save()
    return purchase


# --- Purchase return ------------------------------------------------------------------------
@transaction.atomic
def return_to_supplier(branch, user, *, supplier, reason, reference, items) -> PurchaseReturn:
    """items: [{"batch_id", "quantity"}]. Value = purchase price + GST of the batch."""
    if not reason.strip():
        raise ValidationError({"reason": "Please write why the stock is returned."})
    record = PurchaseReturn.objects.create(
        organization_id=branch.organization_id, branch=branch, supplier=supplier, return_date=timezone.localdate(),
        reference=reference[:60], reason=reason[:200], created_by=user, updated_by=user,
    )
    total = ZERO
    for item in items:
        batch = _locked_batch(branch, item["batch_id"])
        if item["quantity"] <= 0 or item["quantity"] > batch.quantity:
            raise ValidationError({"items": f"{batch.medicine.name} / {batch.batch_no}: only {batch.quantity} available."})
        rate = rupees((batch.purchase_rate or ZERO) * (100 + batch.gst_rate) / 100)
        amount = rupees(rate * item["quantity"])
        batch.quantity -= item["quantity"]
        batch.updated_by = user
        batch.save(update_fields=["quantity", "updated_by", "updated_at"])
        PurchaseReturnItem.objects.create(organization_id=branch.organization_id, purchase_return=record,
                                          medicine=batch.medicine, batch=batch, quantity=item["quantity"], rate=rate,
                                          amount=amount, created_by=user, updated_by=user)
        _move(batch, "purchase_return", -item["quantity"], user, reason=reason, reference=record.id,
              label=f"Return to {supplier.name}" if supplier else "Return to supplier")
        total += amount
    record.total_amount = total
    record.save(update_fields=["total_amount"])
    return record


# --- Corrections ---------------------------------------------------------------------------------
CORRECTION_KINDS = ("adjust", "damaged", "expired")


@transaction.atomic
def correct_stock(batch_id, branch, change: Decimal, reason: str, user, kind="adjust") -> StockBatch:
    """Damaged / expired (stock out) or a manual correction (+/-). A reason is required."""
    if kind not in CORRECTION_KINDS:
        raise ValidationError({"kind": "Unknown type of correction."})
    if not reason.strip():
        raise ValidationError({"reason": "Please write why the stock is corrected."})
    if kind in ("damaged", "expired") and change > 0:
        change = -change
    batch = _locked_batch(branch, batch_id)
    if batch.quantity + change < 0:
        raise ValidationError({"quantity": f"Only {batch.quantity} available."})
    batch.quantity += change
    batch.updated_by = user
    batch.save(update_fields=["quantity", "updated_by", "updated_at"])
    _move(batch, kind, change, user, reason=reason)
    return batch


# --- Selling (dispensing a prescription) -------------------------------------------------------
def suggested_batches(branch, medicine_ids) -> dict:
    """{medicine_id: [batches with stock, not expired, earliest expiry first]} - FEFO."""
    today = timezone.localdate()
    batches = (StockBatch.objects.filter(branch=branch, medicine_id__in=medicine_ids, quantity__gt=0)
               .filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=today))
               .order_by("expiry_date", "created_at"))
    result = {}
    for b in batches:
        result.setdefault(b.medicine_id, []).append(b)
    return result


def dispensed_quantities(prescription) -> dict:
    """{prescription_item_id: packs given (after returns)}"""
    result = {}
    for item in DispenseItem.objects.filter(dispense__prescription=prescription, prescription_item__isnull=False):
        result[item.prescription_item_id] = result.get(item.prescription_item_id, ZERO) + item.quantity - item.returned_quantity
    return {k: v for k, v in result.items() if v > 0}


def dispense_status(prescription) -> str:
    """'pending' (nothing given), 'partly', or 'done' (every stock medicine given)."""
    stock_items = [i for i in prescription.items.all() if i.medicine_id]
    if not stock_items:
        return "pending"
    given = dispensed_quantities(prescription)
    count = sum(1 for i in stock_items if given.get(i.id))
    return "pending" if count == 0 else ("done" if count == len(stock_items) else "partly")


def _unit_label(medicine, loose_units=None):
    if loose_units:
        unit = medicine.dose_unit.label if medicine.dose_unit_id else "units"
        return f"{unit}"
    # The pack size is already in the item name, so the quantity reads "1 bottle" or "1 pack"
    return medicine.pack_type.label if medicine.pack_type_id else "pack"


@transaction.atomic
def sell(prescription, branch, user, lines: list[dict], *, notes="", payment=None, make_bill=True, bill_to_opd=False):
    """
    Give medicines for a final prescription and make the bill (make_bill=False: only give, no bill).
    bill_to_opd=True ("one combined bill"): the medicines go on the visit's OPD bill instead of a pharmacy bill.
    lines: [{"prescription_item", "batch_id", "quantity" (packs) or "loose_units", "discount_percent"}]
    payment: {"mode": "cash"|"upi"|"card", "amount", "reference"} or None (pay later)
    Returns (dispense, invoice or None).
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
    invoice_lines = []
    total = ZERO
    for line in lines:
        item = line["prescription_item"]
        if item.prescription_id != prescription.id or not item.medicine_id:
            raise ValidationError({"items": "A line does not belong to this prescription."})
        batch = _locked_batch(branch, line["batch_id"])
        medicine = batch.medicine
        if batch.medicine_id != item.medicine_id:
            raise ValidationError({"items": f"{item.medicine_name}: choose a batch of this medicine."})
        if batch.expiry_date and batch.expiry_date < today:
            raise ValidationError({"items": f"{item.medicine_name}: batch {batch.batch_no} has expired."})
        loose = line.get("loose_units")
        if loose:
            if not (medicine.allow_loose and medicine.units_per_pack):
                raise ValidationError({"items": f"{medicine.name} cannot be sold loose."})
            quantity = (Decimal(loose) / medicine.units_per_pack).quantize(Decimal("0.001"))
        else:
            quantity = Decimal(line["quantity"])
        if quantity <= 0:
            raise ValidationError({"items": f"{item.medicine_name}: quantity must be more than 0."})
        if batch.quantity < quantity:
            raise ValidationError({"items": f"{item.medicine_name}: only {batch.quantity.normalize()} left in batch {batch.batch_no}."})
        discount = Decimal(line.get("discount_percent") or 0)
        if not 0 <= discount <= 100:
            raise ValidationError({"items": "Discount must be between 0 and 100 %."})
        price = batch.sale_price
        unit_price = rupees(price / medicine.units_per_pack) if loose else price
        bill_qty = Decimal(loose) if loose else quantity
        amount = rupees(unit_price * bill_qty * (100 - discount) / 100)
        batch.quantity -= quantity
        batch.updated_by = user
        batch.save(update_fields=["quantity", "updated_by", "updated_at"])
        sold = DispenseItem.objects.create(
            organization_id=branch.organization_id, dispense=record, prescription_item=item, medicine=medicine,
            batch=batch, quantity=quantity, loose_units=loose or None, mrp=price, discount_percent=discount,
            amount=amount, created_by=user, updated_by=user,
        )
        _move(batch, "dispense", -quantity, user, reason=f"Rx of {prescription.patient.full_name}", reference=record.id)
        invoice_lines.append({
            "kind": "medicine", "description": f"{medicine.name}{f' ({medicine.pack_size})' if medicine.pack_size else ''}",
            "medicine": medicine, "batch": batch, "dispense_item": sold, "batch_no": batch.batch_no,
            "expiry_date": batch.expiry_date, "hsn_code": medicine.hsn_code, "quantity": bill_qty,
            "unit_label": _unit_label(medicine, loose), "unit_price": unit_price, "discount_percent": discount,
            "gst_rate": batch.gst_rate,
        })
        total += amount
    record.total_amount = total
    record.save(update_fields=["total_amount"])
    if not make_bill:
        return record, None
    if bill_to_opd:
        from apps.billing.opd import add_medicines_to_opd

        invoice = add_medicines_to_opd(branch, user, prescription=prescription, lines=invoice_lines)
    else:
        invoice = create_invoice(branch, user, series="PH", lines=invoice_lines, patient=prescription.patient,
                                 prescription=prescription, dispense=record, notes=notes,
                                 doctor=prescription.doctor)
    # Ledger lines show the bill number
    StockMovement.objects.filter(reference=str(record.id)).update(reference_label=invoice.number)
    if payment and Decimal(payment.get("amount") or 0) > 0:
        record_payment(invoice, user, mode=payment["mode"], amount=min(Decimal(payment["amount"]), invoice.balance),
                       reference=payment.get("reference", ""))
        invoice.refresh_from_db()
    return record, invoice


@transaction.atomic
def take_back(dispense, branch, user, *, items, reason, refund_mode="cash"):
    """
    Sale return. items: [{"dispense_item", "quantity" (packs), "back_to_stock"}].
    Stock goes back up (unless damaged) and a credit note is made on the bill.
    """
    if dispense.branch_id != branch.id:
        raise ValidationError({"detail": "This sale belongs to another branch."})
    invoice = invoice_for_dispense(dispense)
    record = SaleReturn.objects.create(organization_id=branch.organization_id, branch=branch, dispense=dispense,
                                       patient_id=dispense.patient_id, reason=reason[:200], created_by=user, updated_by=user)
    credit_items = []
    total = ZERO
    for entry in items:
        sold: DispenseItem = DispenseItem.objects.select_for_update().get(pk=entry["dispense_item"].pk)
        quantity = Decimal(entry["quantity"])
        left = sold.quantity - sold.returned_quantity
        if quantity <= 0 or quantity > left:
            raise ValidationError({"items": f"{sold.medicine.name}: only {left.normalize()} can be returned."})
        share = quantity / sold.quantity
        amount = rupees(sold.amount * share)
        sold.returned_quantity += quantity
        sold.save(update_fields=["returned_quantity"])
        batch = _locked_batch(branch, sold.batch_id)
        back = entry.get("back_to_stock", True)
        if back:
            batch.quantity += quantity
            batch.updated_by = user
            batch.save(update_fields=["quantity", "updated_by", "updated_at"])
            _move(batch, "sale_return", quantity, user, reason=reason, reference=record.id,
                  label=invoice.number if invoice else "")
        SaleReturnItem.objects.create(organization_id=branch.organization_id, sale_return=record, dispense_item=sold,
                                      batch=batch, quantity=quantity, amount=amount, back_to_stock=back,
                                      created_by=user, updated_by=user)
        if invoice:
            line = invoice.lines.get(dispense_item=sold)
            credit_items.append((line, (line.quantity * share).quantize(Decimal("0.001"))))
        total += amount
    record.total_amount = total
    record.save(update_fields=["total_amount"])
    note = None
    if invoice and credit_items:
        note = create_credit_note(invoice, user, items=credit_items, reason=reason, refund_mode=refund_mode,
                                  sale_return=record)
    return record, note


# --- Physical stock check ---------------------------------------------------------------------
@transaction.atomic
def start_verification(branch, user, *, title, rack=None, notes="") -> StockVerification:
    """Freeze the system quantity of every batch in stock (optionally one rack) for counting."""
    if StockVerification.objects.filter(branch=branch, status="open").exists():
        raise ValidationError({"detail": "A stock check is already open. Complete it first."})
    check = StockVerification.objects.create(organization_id=branch.organization_id, branch=branch,
                                             title=title[:120], rack=rack, notes=notes[:300],
                                             created_by=user, updated_by=user)
    batches = StockBatch.objects.filter(branch=branch, quantity__gt=0)
    if rack is not None:
        on_rack = ProductLocation.objects.filter(branch=branch, rack=rack).values("medicine_id")
        batches = batches.filter(medicine_id__in=on_rack)
    StockVerificationItem.objects.bulk_create([
        StockVerificationItem(organization_id=branch.organization_id, verification=check, batch=b,
                              system_quantity=b.quantity, created_by=user, updated_by=user)
        for b in batches
    ])
    return check


@transaction.atomic
def complete_verification(check: StockVerification, user) -> dict:
    """Post the differences (counted - system) to the ledger. Uncounted lines are left as they are."""
    check = StockVerification.objects.select_for_update().get(pk=check.pk)
    if check.status != "open":
        raise ValidationError({"detail": "This stock check is already completed."})
    changed = 0
    for item in check.items.select_related("batch"):
        if item.counted_quantity is None:
            continue
        batch = _locked_batch(check.branch, item.batch_id)
        # Sales after the count started are kept: difference is against the frozen system quantity
        difference = item.counted_quantity - item.system_quantity
        if difference == 0:
            continue
        if batch.quantity + difference < 0:
            raise ValidationError({"items": f"{batch.medicine.name} / {batch.batch_no}: count is lower than possible."})
        batch.quantity += difference
        batch.updated_by = user
        batch.save(update_fields=["quantity", "updated_by", "updated_at"])
        _move(batch, "verification", difference, user, reason=check.title, reference=check.id, label=check.title)
        changed += 1
    check.status = "completed"
    check.completed_at = timezone.now()
    check.updated_by = user
    check.save(update_fields=["status", "completed_at", "updated_by", "updated_at"])
    return {"changed": changed}


# --- Racks and locations ------------------------------------------------------------------------
def set_location(medicine, branch, user, *, rack=None, shelf="", bin_=""):
    row = ProductLocation.objects.filter(branch=branch, medicine=medicine).first()
    if row is None:
        row = ProductLocation(organization_id=branch.organization_id, branch=branch, medicine=medicine, created_by=user)
    row.rack, row.shelf, row.bin = rack, shelf[:20], bin_[:20]
    row.updated_by = user
    row.save()
    return row


def locations_for(branch, medicine_ids=None) -> dict:
    qs = ProductLocation.objects.filter(branch=branch).select_related("rack")
    if medicine_ids is not None:
        qs = qs.filter(medicine_id__in=medicine_ids)
    return {row.medicine_id: row for row in qs}


def set_reorder_level(medicine, branch, level, user):
    row = BranchMedicine.objects.filter(branch=branch, medicine=medicine).first()
    if row is None:
        row = BranchMedicine(organization_id=medicine.organization_id, branch=branch, medicine=medicine, created_by=user)
    row.reorder_level = level
    row.updated_by = user
    row.save()
    return row


# --- Stock summary and alerts ----------------------------------------------------------------------
def stock_summary(branch, search="", show="all", rack_id=None):
    """
    One row per medicine in this branch's stock (or with a minimum level set).
    show: all | low | out | expiring | expired
    """
    today = timezone.localdate()
    soon = today + timedelta(days=EXPIRY_WARNING_DAYS)
    # First pick the medicines, then add up their stock (separate steps, so totals are never counted twice)
    with_stock = StockBatch.objects.filter(branch=branch).values("medicine_id")
    with_level = BranchMedicine.objects.filter(branch=branch, reorder_level__isnull=False).values("medicine_id")
    medicines = Medicine.objects.filter(organization_id=branch.organization_id).filter(
        Q(id__in=with_stock) | Q(id__in=with_level)
    ).select_related("category", "pack_type")
    if search:
        from apps.medicines.services import search_filter

        medicines = medicines.filter(search_filter(search) | Q(barcode=search)
                                     | Q(batches__branch=branch, batches__batch_no__iexact=search)).distinct()
    locations = locations_for(branch)
    if rack_id:
        medicines = medicines.filter(id__in=[m for m, loc in locations.items() if str(loc.rack_id) == str(rack_id)])
    batches = StockBatch.objects.filter(branch=branch, medicine_id__in=medicines.values("id"), quantity__gt=0)
    sums = {}
    for b in batches.values("medicine_id", "quantity", "expiry_date"):
        s = sums.setdefault(b["medicine_id"], {"available": ZERO, "usable": ZERO, "nearest": None, "near_qty": ZERO})
        s["available"] += b["quantity"]
        if b["expiry_date"] is None or b["expiry_date"] >= today:
            s["usable"] += b["quantity"]
            if b["expiry_date"] and (s["nearest"] is None or b["expiry_date"] < s["nearest"]):
                s["nearest"] = b["expiry_date"]
            if b["expiry_date"] and b["expiry_date"] <= soon:
                s["near_qty"] += b["quantity"]
    levels = dict(BranchMedicine.objects.filter(branch=branch).values_list("medicine_id", "reorder_level"))
    rows = []
    for m in medicines.order_by("name"):
        s = sums.get(m.id, {"available": ZERO, "usable": ZERO, "nearest": None, "near_qty": ZERO})
        level = levels.get(m.id)
        loc = locations.get(m.id)
        row = {
            "medicine": m, "available": s["available"], "usable": s["usable"], "nearest_expiry": s["nearest"],
            "near_expiry_quantity": s["near_qty"], "reorder_level": level,
            "location": loc.label if loc else "", "rack_id": loc.rack_id if loc else None,
            "shelf": loc.shelf if loc else "", "bin": loc.bin if loc else "",
            "out": s["usable"] <= 0,
            "low": level is not None and 0 < s["usable"] <= level,
            "expired": s["available"] > s["usable"],
            "expiring": s["near_qty"] > 0,
        }
        if show != "all" and not row.get(show):
            continue
        rows.append(row)
    return rows


def alert_counts(branch) -> dict:
    rows = stock_summary(branch)
    return {key: sum(1 for r in rows if r[key]) for key in ("low", "out", "expiring", "expired")}


# --- Barcode scan -----------------------------------------------------------------------------------
def scan(branch, code: str) -> dict:
    """
    A scanned code: a batch barcode, a batch number, or a product barcode.
    Returns the medicine and its usable batches (FEFO), the scanned batch first.
    """
    code = code.strip()
    if not code:
        raise ValidationError({"code": "Nothing scanned."})
    batch = (StockBatch.objects.filter(branch=branch).filter(Q(barcode=code) | Q(batch_no__iexact=code))
             .select_related("medicine").order_by("-quantity").first())
    medicine = batch.medicine if batch else Medicine.objects.filter(organization_id=branch.organization_id,
                                                                    barcode=code).first()
    if medicine is None:
        raise ValidationError({"code": f"No medicine or batch found for '{code}'."})
    batches = suggested_batches(branch, [medicine.id]).get(medicine.id, [])
    if batch and batch in batches:
        batches = [batch] + [b for b in batches if b.id != batch.id]
    return {"medicine": medicine, "batch": batch, "batches": batches}


# --- Stock ledger --------------------------------------------------------------------------------------
def ledger(branch, *, medicine_id=None, kind=None, date_from=None, date_to=None, batch_id=None):
    """Movements in a period, plus a statement: opening balance, totals per kind, closing balance."""
    qs = StockMovement.objects.filter(branch=branch).select_related("batch", "medicine", "created_by")
    if medicine_id:
        qs = qs.filter(medicine_id=medicine_id)
    if batch_id:
        qs = qs.filter(batch_id=batch_id)
    before = qs.filter(created_at__date__lt=date_from) if date_from else qs.none()
    period = qs
    if date_from:
        period = period.filter(created_at__date__gte=date_from)
    if date_to:
        period = period.filter(created_at__date__lte=date_to)
    opening = before.aggregate(s=Sum("quantity"))["s"] or ZERO
    by_kind = {row["kind"]: row["s"] for row in period.values("kind").annotate(s=Sum("quantity"))}
    closing = opening + sum(by_kind.values(), ZERO)
    lines = period.filter(kind=kind) if kind else period
    return {"opening": opening, "by_kind": by_kind, "closing": closing, "lines": lines.order_by("-created_at")[:500]}

