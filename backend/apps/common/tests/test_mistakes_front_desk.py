"""
"By mistake" tests: wrong input, a double click, the wrong option, the wrong person.
Each test says what SHOULD happen when a person makes a mistake: the app refuses politely (400/403/404), nothing is
half-saved, and nothing is deleted. Front desk: patients, appointments, billing.
"""
from datetime import date, time, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.accounts.models import DoctorSchedule
from apps.appointments.models import Appointment
from apps.billing.models import Invoice
from apps.billing.services import create_invoice, record_payment
from apps.patients.models import Patient
from conftest import client_for

PATIENTS = "/api/v1/patients/"
APPTS = "/api/v1/appointments/"
INVOICES = "/api/v1/invoices/"


def today():
    return timezone.localdate()


@pytest.fixture
def schedule(org, doctor, branch_a):
    for weekday in range(7):
        DoctorSchedule.objects.create(organization=org, branch=branch_a, doctor=doctor, weekday=weekday,
                                      start_time=time(10, 0), end_time=time(13, 0), slot_minutes=15)


@pytest.fixture
def patient(org, roles):
    return Patient.objects.create(organization=org, uhid="1", first_name="Ramesh", last_name="Patel", gender="male",
                                  mobile="9876543210")


def reg(client, **extra):
    data = {"first_name": "Test", "last_name": "Patient", "gender": "female", "age": 40, "mobile": "9876543210", **extra}
    return client.post(PATIENTS, data, format="json")


# ---------------------------------------------------------------- patients
@pytest.mark.django_db
@pytest.mark.parametrize("bad", [
    {"first_name": "   "},                       # only spaces
    {"first_name": ""},                          # empty name
    {"mobile": "98765"},                         # too short
    {"mobile": "abcdefghij"},                    # letters
    {"mobile": "1234567890"},                    # does not start with 6-9
    {"age": 200},                                # impossible age
    {"age": -3},                                 # negative age
    {"age": None, "date_of_birth": str(today() + timedelta(days=5))},  # born in the future
    {"gender": "robot"},                         # not an option
    {"pincode": "12"},
    {"email": "not-an-email"},
])
def test_registration_refuses_wrong_input(receptionist, branch_a, bad):
    res = reg(client_for(receptionist, branch_a), **bad)
    assert res.status_code == 400, (bad, res.data)
    assert Patient.objects.count() == 0  # nothing half-saved


@pytest.mark.django_db
def test_double_click_register_does_not_crash(receptionist, branch_a):
    client = client_for(receptionist, branch_a)
    first, second = reg(client), reg(client)
    assert first.status_code == 201
    # The same mobile again is allowed (a family shares a phone) but the two get different numbers, and the
    # duplicate check helps the desk notice it.
    assert second.status_code in (201, 400) and first.data["uhid"] != (second.data.get("uhid") or "")
    dup = client.get(PATIENTS + "duplicates/", {"mobile": "9876543210"})
    assert dup.status_code == 200


@pytest.mark.django_db
def test_wrong_people_cannot_change_patients(therapist, pharmacist, doctor, branch_a, patient):
    assert client_for(therapist, branch_a).patch(f"{PATIENTS}{patient.id}/", {"city": "X"}, format="json").status_code == 403
    assert client_for(pharmacist, branch_a).post(PATIENTS, {"first_name": "A", "last_name": "B", "gender": "male",
                                                           "age": 30, "mobile": "9876500001"}, format="json").status_code == 403
    assert client_for(therapist, branch_a).delete(f"{PATIENTS}{patient.id}/").status_code in (403, 405)


@pytest.mark.django_db
def test_deleting_a_patient_never_removes_the_record(receptionist, branch_admin, branch_a, patient):
    for user in (receptionist, branch_admin):
        res = client_for(user, branch_a).delete(f"{PATIENTS}{patient.id}/")
        assert res.status_code in (200, 204, 403, 405)
    assert Patient.all_objects.filter(pk=patient.pk).exists()  # at most marked as deleted


@pytest.mark.django_db
def test_other_clinic_cannot_see_patient(roles, patient, org, branch_a):
    from apps.accounts.models import User
    from apps.organizations.models import Branch, Organization

    other_org = Organization.objects.create(name="Other Clinic")
    other_branch = Branch.objects.create(organization=other_org, name="X", code="X")
    stranger = User.objects.create_user(username="stranger", password="Test@Clinic2026", full_name="S", organization=other_org,
                                        is_org_admin=True)
    client = client_for(stranger, other_branch)
    assert client.get(f"{PATIENTS}{patient.id}/").status_code == 404
    assert client.get(PATIENTS).data["count"] == 0


# ---------------------------------------------------------------- appointments
def book(client, patient, doctor, day=None, start="10:00", **extra):
    return client.post(APPTS, {"patient": str(patient.id), "doctor": str(doctor.id),
                               "date": str(day or today() + timedelta(days=1)), "start_time": start, **extra}, format="json")


@pytest.mark.django_db
def test_booking_mistakes(receptionist, doctor, branch_a, branch_b, schedule, patient):
    c = client_for(receptionist, branch_a)
    assert book(c, patient, doctor, day=today() - timedelta(days=2)).status_code == 400   # in the past
    assert book(c, patient, doctor, start="08:00").status_code == 400                      # doctor not sitting then
    assert book(c, patient, doctor, start="10:07").status_code == 400                      # not a slot start
    assert book(c, patient, doctor, start="25:00").status_code == 400                      # not a time
    assert c.post(APPTS, {"patient": "not-an-id", "doctor": str(doctor.id), "date": str(today())}, format="json").status_code == 400
    assert c.post(APPTS, {}, format="json").status_code == 400                              # nothing chosen
    ok = book(c, patient, doctor)
    assert ok.status_code == 201
    assert book(c, patient, doctor, start="10:15").status_code == 400                      # same patient, same doctor, same day
    other = Patient.objects.create(organization=patient.organization, uhid="2", first_name="A", last_name="B", gender="male",
                                   mobile="9876500002")
    assert book(c, other, doctor).status_code == 400                                       # same slot, someone else
    assert Appointment.objects.count() == 1


@pytest.mark.django_db
def test_wrong_branch_doctor_is_refused(receptionist, doctor, branch_b, branch_a, schedule, patient):
    # branch B has no schedule for this doctor; the receptionist only works in A
    assert client_for(receptionist, branch_b).get(APPTS).status_code == 403
    res = client_for(receptionist, branch_a).post(APPTS, {"patient": str(patient.id), "doctor": str(receptionist.id),
                                                          "date": str(today() + timedelta(days=1)), "start_time": "10:00"},
                                                  format="json")
    assert res.status_code == 400  # the receptionist is not a doctor


@pytest.mark.django_db
def test_double_click_on_check_in_gives_one_token(org, receptionist, doctor, branch_a, schedule, patient):
    appt = Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, date=today(),
                                      start_time=time(10, 0), end_time=time(10, 15))
    c = client_for(receptionist, branch_a)
    first = c.post(f"{APPTS}{appt.id}/check-in/")
    second = c.post(f"{APPTS}{appt.id}/check-in/")
    assert first.status_code == 200 and second.status_code == 400
    appt.refresh_from_db()
    assert appt.token_number == 1 and appt.status == "checked_in"


@pytest.mark.django_db
def test_wrong_step_order_is_refused(org, receptionist, doctor, branch_a, schedule, patient):
    appt = Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor, date=today(),
                                      start_time=time(10, 0), end_time=time(10, 15))
    c = client_for(receptionist, branch_a)
    assert c.post(f"{APPTS}{appt.id}/start/").status_code == 400      # not checked in yet
    assert c.post(f"{APPTS}{appt.id}/complete/").status_code == 400   # not checked in yet
    assert c.post(f"{APPTS}{appt.id}/cancel/", {"reason": "x"}, format="json").status_code == 200
    for step in ("check-in", "start", "complete", "no-show"):
        assert c.post(f"{APPTS}{appt.id}/{step}/").status_code == 400, step  # cancelled can not go on
    assert c.post(f"{APPTS}{appt.id}/cancel/", {"reason": "again"}, format="json").status_code == 400  # cancel twice


@pytest.mark.django_db
def test_check_in_on_the_wrong_day_is_refused(org, receptionist, doctor, branch_a, schedule, patient):
    tomorrow = Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                          date=today() + timedelta(days=1), start_time=time(10, 0), end_time=time(10, 15))
    assert client_for(receptionist, branch_a).post(f"{APPTS}{tomorrow.id}/check-in/").status_code == 400


@pytest.mark.django_db
def test_reschedule_mistakes(org, receptionist, doctor, branch_a, schedule, patient):
    appt = Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                      date=today() + timedelta(days=1), start_time=time(10, 0), end_time=time(10, 15))
    c = client_for(receptionist, branch_a)
    assert c.post(f"{APPTS}{appt.id}/reschedule/", {"date": str(today() - timedelta(days=1)), "start_time": "10:00"},
                  format="json").status_code == 400
    assert c.post(f"{APPTS}{appt.id}/reschedule/", {"date": str(today() + timedelta(days=2)), "start_time": "18:00"},
                  format="json").status_code == 400
    appt.refresh_from_db()
    assert appt.date == today() + timedelta(days=1) and appt.start_time == time(10, 0)  # unchanged after the refusals


@pytest.mark.django_db
def test_other_branch_appointment_is_not_reachable(org, receptionist, doctor, branch_a, branch_b, schedule, patient):
    appt = Appointment.objects.create(organization=org, branch=branch_b, patient=patient, doctor=doctor, date=today(),
                                      start_time=time(10, 0), end_time=time(10, 15))
    assert client_for(receptionist, branch_a).get(f"{APPTS}{appt.id}/").status_code == 404
    assert client_for(receptionist, branch_a).post(f"{APPTS}{appt.id}/check-in/").status_code == 404


# ---------------------------------------------------------------- billing
def make_invoice(branch, user, price="500", qty="1"):
    return create_invoice(branch, user, series="OP", lines=[
        {"kind": "consultation", "description": "Consultation", "quantity": qty, "unit_price": price, "gst_rate": 0}])


@pytest.mark.django_db
@pytest.mark.parametrize("pay", [
    {"mode": "cash", "amount": "0"}, {"mode": "cash", "amount": "-50"}, {"mode": "cash", "amount": "abc"},
    {"mode": "cash", "amount": "99999"}, {"mode": "bitcoin", "amount": "10"}, {"mode": "cash"}, {"amount": "10"},
])
def test_wrong_payments_are_refused(receptionist, branch_a, pay):
    invoice = make_invoice(branch_a, receptionist)
    res = client_for(receptionist, branch_a).post(f"{INVOICES}{invoice.id}/pay/", pay, format="json")
    assert res.status_code == 400, (pay, res.data)
    invoice.refresh_from_db()
    assert invoice.paid_amount == 0 and invoice.status == "unpaid"


@pytest.mark.django_db
def test_paying_twice_by_double_click_never_overpays(receptionist, branch_a):
    invoice = make_invoice(branch_a, receptionist, price="500")
    c = client_for(receptionist, branch_a)
    assert c.post(f"{INVOICES}{invoice.id}/pay/", {"mode": "cash", "amount": "500"}, format="json").status_code == 200
    assert c.post(f"{INVOICES}{invoice.id}/pay/", {"mode": "cash", "amount": "500"}, format="json").status_code == 400
    invoice.refresh_from_db()
    assert invoice.paid_amount == Decimal("500.00") and invoice.status == "paid"


@pytest.mark.django_db
def test_cancel_mistakes(receptionist, branch_admin, branch_a):
    invoice = make_invoice(branch_a, receptionist)
    record_payment(invoice, receptionist, mode="cash", amount=Decimal("500"))
    admin = client_for(branch_admin, branch_a)
    assert admin.post(f"{INVOICES}{invoice.id}/cancel/", {}, format="json").status_code == 400            # no reason given
    assert admin.post(f"{INVOICES}{invoice.id}/cancel/", {"reason": "wrong patient"}, format="json").status_code == 200
    assert admin.post(f"{INVOICES}{invoice.id}/cancel/", {"reason": "again"}, format="json").status_code == 400  # twice
    pay = admin.post(f"{INVOICES}{invoice.id}/pay/", {"mode": "cash", "amount": "10"}, format="json")
    assert pay.status_code == 400                                                                          # paying a cancelled bill
    assert Invoice.all_objects.filter(pk=invoice.pk).exists()                                              # never deleted


@pytest.mark.django_db
def test_invoice_of_another_branch_is_not_reachable(receptionist, branch_a, branch_b, org_admin):
    invoice = make_invoice(branch_b, org_admin)
    c = client_for(receptionist, branch_a)
    assert c.get(f"{INVOICES}{invoice.id}/").status_code == 404
    assert c.post(f"{INVOICES}{invoice.id}/pay/", {"mode": "cash", "amount": "10"}, format="json").status_code == 404


@pytest.mark.django_db
def test_bad_bill_lines_are_refused(receptionist, branch_a):
    from rest_framework.exceptions import ValidationError

    for line in ({"quantity": "0", "unit_price": "100"}, {"quantity": "-1", "unit_price": "100"},
                 {"quantity": "1", "unit_price": "-100"}, {"quantity": "1", "unit_price": "100", "discount_percent": "150"},
                 {"quantity": "1", "unit_price": "100", "gst_rate": "-5"}):
        with pytest.raises((ValidationError, ValueError, Exception)):
            create_invoice(branch_a, receptionist, series="OP", lines=[{"kind": "consultation", "description": "x", **line}])
    assert Invoice.objects.count() == 0
    with pytest.raises(Exception):
        create_invoice(branch_a, receptionist, series="OP", lines=[])  # an empty bill


@pytest.mark.django_db
def test_wrong_people_and_billing(therapist, pharmacist, doctor, branch_a, receptionist):
    invoice = make_invoice(branch_a, receptionist)
    assert client_for(therapist, branch_a).get(INVOICES).status_code == 403
    assert client_for(therapist, branch_a).post(f"{INVOICES}{invoice.id}/pay/", {"mode": "cash", "amount": "10"},
                                                format="json").status_code == 403
    assert client_for(receptionist, branch_a).post(f"{INVOICES}{invoice.id}/cancel/", {"reason": "x"}, format="json").status_code == 403
