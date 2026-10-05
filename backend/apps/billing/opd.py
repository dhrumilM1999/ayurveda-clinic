"""
OPD billing (out-patient): consultation fee at check-in, services & charges after the check-up, and medicines
when the clinic chose "one combined bill" (Additional settings). One OPD bill per visit / appointment.
Other modules call these functions; they never change bills directly.
"""
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import HEALTHCARE_SAC, BranchServicePrice, ConsultationFee, Invoice, ServiceCharge
from .services import add_lines, create_invoice, record_payment

LINE_KINDS_FROM_DESK = {"consultation", "service", "other"}


# --- Fees and services -----------------------------------------------------------------------------
def fee_for(branch, doctor) -> ConsultationFee | None:
    return ConsultationFee.objects.filter(branch=branch, doctor=doctor).first()


def suggest_consultation(branch, patient, doctor, day=None) -> dict:
    """
    New case or follow-up, and the fee. Follow-up = this doctor saw the patient within the doctor's
    follow-up days (e.g. 15); otherwise it is charged as a new case.
    """
    from apps.emr.services import last_visit_date

    day = day or timezone.localdate()
    fee = fee_for(branch, doctor)
    last = last_visit_date(patient, doctor, day)
    days = fee.follow_up_days if fee else 15
    follow_up = bool(last and (day - last).days <= days)
    amount = (fee.follow_up_fee if follow_up else fee.new_case_fee) if fee else Decimal("0")
    kind = "follow_up" if follow_up else "new"
    return {
        "visit_kind": kind, "fee": amount, "fee_set": fee is not None, "last_visit": last, "follow_up_days": days,
        "description": consultation_text(doctor, kind),
    }


def consultation_text(doctor, kind: str) -> str:
    label = "Follow-up" if kind == "follow_up" else "New case"
    return f"OPD consultation ({label}) - {doctor.full_name}"


def branch_services(branch, active_only=True) -> list[dict]:
    """Services with this branch's price and on/off."""
    overrides = {o.service_id: o for o in BranchServicePrice.objects.filter(branch=branch)}
    rows = []
    for service in ServiceCharge.objects.filter(organization_id=branch.organization_id).select_related("category"):
        own = overrides.get(service.id)
        active = service.is_active and (own.is_active if own else True)
        if active_only and not active:
            continue
        rows.append({"service": service, "branch_price": own.price if own else None,
                     "price": own.price if own and own.price is not None else service.price, "active": active})
    return rows


# --- The OPD bill ----------------------------------------------------------------------------------
def opd_bill_for(*, appointment=None, visit=None) -> Invoice | None:
    """The open (not cancelled) OPD bill of this visit or appointment, if any."""
    q = Q()
    if visit is not None:
        q |= Q(visit=visit)
        if visit.appointment_id:
            q |= Q(appointment_id=visit.appointment_id)
    if appointment is not None:
        q |= Q(appointment=appointment)
    if not q:
        return None
    invoice = (Invoice.objects.filter(q, series="OP").exclude(status="cancelled").order_by("created_at").first())
    if invoice and visit is not None and invoice.visit_id is None:
        Invoice.objects.filter(pk=invoice.pk).update(visit=visit)  # the check-in bill now belongs to the visit
        invoice.visit = visit
    return invoice


def clean_desk_lines(organization_id, lines: list[dict]) -> list[dict]:
    """Lines typed at the desk / by the doctor: consultation, a service from the list, or another charge."""
    services = {s.id: s for s in ServiceCharge.objects.filter(
        organization_id=organization_id, id__in=[l.get("service") for l in lines if l.get("service")])}
    clean = []
    for line in lines:
        kind = line.get("kind", "other")
        if kind not in LINE_KINDS_FROM_DESK:
            raise ValidationError({"lines": "Unknown kind of line."})
        price, qty = Decimal(line["unit_price"]), Decimal(line.get("quantity") or 1)
        discount = Decimal(line.get("discount_percent") or 0)
        if price < 0 or qty <= 0 or not 0 <= discount <= 100:
            raise ValidationError({"lines": "Check the price, quantity and discount."})
        service = services.get(line.get("service")) if line.get("service") else None
        if line.get("service") and service is None:
            raise ValidationError({"lines": "A service was not found."})
        description = (line.get("description") or (service.name if service else "")).strip()
        if not description:
            raise ValidationError({"lines": "Each line needs a description."})
        clean.append({
            "kind": kind, "service": service, "description": description, "quantity": qty, "unit_price": price,
            "discount_percent": discount, "gst_rate": service.gst_rate if service else Decimal("0"),
            "hsn_code": (service.sac_code if service else HEALTHCARE_SAC), "unit_label": "",
        })
    return clean


@transaction.atomic
def charge_opd(branch, user, *, patient, doctor, lines: list[dict], appointment=None, visit=None,
               payment: dict | None = None) -> Invoice:
    """
    Put charges on the patient's OPD bill for this visit / appointment: makes the bill the first time
    (e.g. consultation fee at check-in), adds lines after that (services after the check-up).
    payment: {"mode", "amount", "reference"} taken now, or None (pay later).
    """
    invoice = opd_bill_for(appointment=appointment, visit=visit)
    if invoice is None:
        invoice = create_invoice(branch, user, series="OP", care_type="OPD", lines=lines, patient=patient,
                                 doctor=doctor, appointment=appointment or (visit.appointment if visit else None),
                                 visit=visit)
    else:
        if invoice.branch_id != branch.id:
            raise ValidationError({"detail": "This bill belongs to another branch."})
        invoice = add_lines(invoice, user, lines)
    if payment and Decimal(payment.get("amount") or 0) > 0:
        record_payment(invoice, user, mode=payment["mode"], amount=min(Decimal(payment["amount"]), invoice.balance),
                       reference=payment.get("reference", ""))
        invoice.refresh_from_db()
    return invoice


def add_medicines_to_opd(branch, user, *, prescription, lines: list[dict]) -> Invoice:
    """'One combined bill': medicines given by the pharmacy go on the visit's OPD bill."""
    visit = prescription.visit
    return charge_opd(branch, user, patient=prescription.patient, doctor=prescription.doctor, lines=lines,
                      visit=visit, appointment=visit.appointment if visit else None)
