"""
Two people clicking at the same moment (two receptionists, or a double click that slips through).
Bill numbers and token numbers must never repeat.
"""
import threading
from datetime import time

import pytest
from django.db import connection
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.billing.models import Invoice
from apps.billing.services import create_invoice
from apps.patients.models import Patient

pytestmark = pytest.mark.usefixtures("all_additional_features")


def run_together(work, count=8):
    errors, results = [], []
    barrier = threading.Barrier(count)

    def target(i):
        try:
            barrier.wait(timeout=10)
            results.append(work(i))
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))
        finally:
            connection.close()

    threads = [threading.Thread(target=target, args=(i,)) for i in range(count)]
    [t.start() for t in threads]
    [t.join(timeout=60) for t in threads]
    return results, errors


@pytest.mark.django_db(transaction=True)
def test_bill_numbers_never_repeat_when_many_bill_at_once(branch_a, receptionist):
    def work(i):
        invoice = create_invoice(branch_a, receptionist, series="OP", lines=[
            {"kind": "consultation", "description": "x", "quantity": "1", "unit_price": "100", "gst_rate": 0}])
        return invoice.number

    numbers, errors = run_together(work)
    assert not errors, errors
    assert len(numbers) == 8 and len(set(numbers)) == 8
    assert Invoice.objects.count() == 8


@pytest.mark.django_db(transaction=True)
def test_token_numbers_never_repeat_when_many_check_in_at_once(org, roles, branch_a, doctor, receptionist):
    from apps.appointments.services import change_status

    patients = [Patient.objects.create(organization=org, uhid=str(i + 1), first_name=f"P{i}", last_name="T", gender="male",
                                       mobile=f"98765000{i:02d}") for i in range(8)]
    appts = [Appointment.objects.create(organization=org, branch=branch_a, patient=p, doctor=doctor, date=timezone.localdate(),
                                        start_time=time(10, i), end_time=time(10, i + 1)) for i, p in enumerate(patients)]

    def work(i):
        appt = Appointment.objects.get(pk=appts[i].pk)
        change_status(appt, "check_in", receptionist)
        return appt.token_number

    tokens, errors = run_together(work)
    assert not errors, errors
    assert sorted(tokens) == list(range(1, 9))


@pytest.mark.django_db(transaction=True)
def test_a_bill_cannot_be_overpaid_by_clicks_at_the_same_moment(branch_a, receptionist):
    from decimal import Decimal

    from apps.billing.services import record_payment

    invoice = create_invoice(branch_a, receptionist, series="OP", lines=[
        {"kind": "consultation", "description": "x", "quantity": "1", "unit_price": "100", "gst_rate": 0}])

    def work(i):
        record_payment(Invoice.objects.get(pk=invoice.pk), receptionist, mode="cash", amount=Decimal("100"))
        return True

    ok, errors = run_together(work)
    invoice.refresh_from_db()
    assert invoice.paid_amount == Decimal("100.00") and invoice.status == "paid"
    assert len(ok) == 1 and len(errors) == 7  # one payment went in, the others were refused


@pytest.mark.django_db(transaction=True)
def test_the_last_pack_cannot_be_sold_twice(org, roles, branch_a, pharmacist, doctor):
    from datetime import date, timedelta

    from apps.emr.models import Visit
    from apps.medicines.models import Medicine
    from apps.medicines.services import add_sample_medicines
    from apps.pharmacy.models import StockBatch
    from apps.pharmacy.services import counter_sell

    add_sample_medicines(org)
    medicine = Medicine.objects.filter(organization=org, schedule_e1=False).first()
    batch = StockBatch.objects.create(organization=org, branch=branch_a, medicine=medicine, batch_no="LAST",
                                      expiry_date=date.today() + timedelta(days=300), quantity=1, mrp="100", selling_price="100")

    def work(i):
        counter_sell(branch_a, pharmacist, [{"batch_id": batch.id, "quantity": "1"}])
        return True

    ok, errors = run_together(work)
    batch.refresh_from_db()
    assert batch.quantity == 0 and len(ok) == 1, (batch.quantity, len(ok), errors[:2])
