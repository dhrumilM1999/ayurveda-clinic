from datetime import time, timedelta
from urllib.parse import unquote

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import DoctorSchedule
from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.notifications.sms import FakeSmsProvider
from apps.notifications.whatsapp import FakeWhatsAppProvider, whatsapp_number
from apps.organizations.models import Branch, BranchFeatureFlag
from apps.patients.models import ConsentPurpose, Patient, PatientConsent
from conftest import client_for, make_user

URL = "/api/v1/appointments/"


def tomorrow():
    return timezone.localdate() + timedelta(days=1)


@pytest.fixture
def schedule(org, doctor, branch_a):
    """The doctor sits in branch A every day, 10:00-13:00, 15-minute slots (12 slots)."""
    for weekday in range(7):
        DoctorSchedule.objects.create(organization=org, branch=branch_a, doctor=doctor, weekday=weekday,
                                      start_time=time(10, 0), end_time=time(13, 0), slot_minutes=15)


def make_patient(org, mobile="9876543210", first="Ramesh", last="Patel", consent=True):
    patient = Patient.objects.create(organization=org, uhid=f"T-{mobile}", first_name=first, last_name=last,
                                     gender="male", mobile=mobile, preferred_language="en")
    if consent:
        purpose = ConsentPurpose.objects.get(organization=org, code="communication")
        branch = Branch.objects.filter(organization=org).first()
        PatientConsent.objects.create(organization=org, patient=patient, branch=branch, purpose=purpose,
                                      purpose_version=purpose.version, granted=True,
                                      method="verbal", language="en")
    return patient


@pytest.fixture
def patient(org, roles, branch_a):
    return make_patient(org)


def book(client, patient, doctor, day=None, start="10:00", **extra):
    payload = {"patient": str(patient.id), "doctor": str(doctor.id), "date": str(day or tomorrow()),
               "start_time": start, **extra}
    return client.post(URL, payload, format="json")


def today_appointment(org, branch, patient, doctor, start=time(10, 0)):
    """An appointment for today, created directly (the slot may already be in the past)."""
    return Appointment.objects.create(organization=org, branch=branch, patient=patient, doctor=doctor,
                                      date=timezone.localdate(), start_time=start, end_time=time(10, 15))


# --- Slots ------------------------------------------------------------------------
@pytest.mark.django_db
def test_slots_come_from_doctor_schedule(receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    book(client, patient, doctor, start="10:30")
    res = client.get(URL + "slots/", {"doctor": doctor.id, "date": str(tomorrow())})
    assert res.status_code == 200
    slots = res.data["slots"]
    assert len(slots) == 12
    assert slots[0] == {"start": "10:00", "end": "10:15", "status": "free"}
    assert slots[2]["status"] == "booked"


@pytest.mark.django_db
def test_doctors_list_shows_who_sits(receptionist, doctor, branch_a, schedule):
    res = client_for(receptionist, branch_a).get(URL + "doctors/", {"date": str(tomorrow())})
    assert res.status_code == 200
    assert res.data[0]["sits"] is True and res.data[0]["timings"] == ["10:00–13:00"]


# --- Booking ------------------------------------------------------------------------
@pytest.mark.django_db
def test_book_appointment_sends_sms_and_whatsapp_link(receptionist, doctor, branch_a, schedule, patient):
    res = book(client_for(receptionist, branch_a), patient, doctor, start="11:00")
    assert res.status_code == 201, res.data
    assert res.data["status"] == "booked"
    assert res.data["end_time"] == "11:15:00"
    assert res.data["patient_detail"]["mobile_masked"] == "98XXXXXX10"
    note = res.data["notification"]
    assert note["consent"] is True and note["sms_sent"] is True
    assert note["whatsapp_link"].startswith("https://wa.me/919876543210?text=")
    assert "11:00 AM" in unquote(note["whatsapp_link"])
    assert FakeSmsProvider.outbox[-1]["to"] == "9876543210"
    assert AuditLog.objects.filter(action="create", object_type="appointments.appointment").exists()


@pytest.mark.django_db
def test_no_messages_without_consent(org, receptionist, doctor, branch_a, schedule, roles):
    patient = make_patient(org, consent=False)
    res = book(client_for(receptionist, branch_a), patient, doctor)
    assert res.status_code == 201
    assert res.data["notification"] == {"consent": False, "sms_sent": False, "whatsapp_link": "", "message": ""}
    assert FakeSmsProvider.outbox == [] and FakeWhatsAppProvider.outbox == []


@pytest.mark.django_db
def test_double_booking_is_refused(org, receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    assert book(client, patient, doctor).status_code == 201
    other = make_patient(org, mobile="9876500000", first="Sunita")
    res = book(client, other, doctor)
    assert res.status_code == 400
    assert "already booked" in str(res.data["start_time"])


@pytest.mark.django_db
def test_database_also_blocks_double_booking(org, branch_a, doctor, patient):
    day = tomorrow()
    Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                               date=day, start_time=time(10, 0))
    other = make_patient(org, mobile="9876500000")
    with pytest.raises(IntegrityError), transaction.atomic():
        Appointment.objects.create(organization=org, branch=branch_a, patient=other, doctor=doctor,
                                   date=day, start_time=time(10, 0))


@pytest.mark.django_db
def test_cancel_frees_the_slot(org, receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    appt_id = book(client, patient, doctor).data["id"]
    res = client.post(f"{URL}{appt_id}/cancel/", {"reason": "Patient travelling"}, format="json")
    assert res.status_code == 200
    assert res.data["status"] == "cancelled" and res.data["cancel_reason"] == "Patient travelling"
    other = make_patient(org, mobile="9876500000")
    assert book(client, other, doctor).status_code == 201


@pytest.mark.django_db
def test_invalid_times_are_refused(receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    assert "does not sit" in str(book(client, patient, doctor, start="15:00").data["start_time"])
    yesterday = timezone.localdate() - timedelta(days=1)
    assert "passed" in str(book(client, patient, doctor, day=yesterday).data["date"])


@pytest.mark.django_db
def test_same_patient_twice_same_day_refused(receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    assert book(client, patient, doctor).status_code == 201
    res = book(client, patient, doctor, start="11:00")
    assert res.status_code == 400 and "patient" in res.data


@pytest.mark.django_db
def test_doctor_must_work_in_branch(org, roles, receptionist, branch_a, branch_b, patient):
    outsider = make_user(org, "doc_b", {branch_b: roles["doctor"]}, is_doctor=True)
    res = book(client_for(receptionist, branch_a), patient, outsider)
    assert res.status_code == 400 and "doctor" in res.data


# --- Walk-in, tokens and the visit flow -------------------------------------------------
@pytest.mark.django_db
def test_walk_in_gets_next_token(org, receptionist, doctor, branch_a, patient):
    client = client_for(receptionist, branch_a)
    first = client.post(URL, {"patient": str(patient.id), "doctor": str(doctor.id), "kind": "walk_in"}, format="json")
    assert first.status_code == 201, first.data
    assert first.data["status"] == "checked_in"
    assert first.data["token_number"] == 1
    assert first.data["date"] == str(timezone.localdate())
    assert "token number" in first.data["notification"]["message"]
    other = make_patient(org, mobile="9876500000")
    second = client.post(URL, {"patient": str(other.id), "doctor": str(doctor.id), "kind": "walk_in"}, format="json")
    assert second.data["token_number"] == 2


@pytest.mark.django_db
def test_check_in_start_complete(org, receptionist, doctor, branch_a, patient):
    appt = today_appointment(org, branch_a, patient, doctor)
    client = client_for(receptionist, branch_a)
    res = client.post(f"{URL}{appt.id}/check-in/")
    assert res.status_code == 200
    assert res.data["status"] == "checked_in" and res.data["token_number"] == 1
    assert client.post(f"{URL}{appt.id}/check-in/").status_code == 400  # not twice
    assert client_for(doctor, branch_a).post(f"{URL}{appt.id}/start/").data["status"] == "in_consultation"
    res = client_for(doctor, branch_a).post(f"{URL}{appt.id}/complete/")
    assert res.data["status"] == "completed" and res.data["completed_at"]
    assert client.post(f"{URL}{appt.id}/cancel/").status_code == 400  # finished visits can't be cancelled


@pytest.mark.django_db
def test_future_appointment_cannot_check_in(receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    appt_id = book(client, patient, doctor).data["id"]
    res = client.post(f"{URL}{appt_id}/check-in/")
    assert res.status_code == 400 and "day of the appointment" in str(res.data)


@pytest.mark.django_db
def test_reschedule_moves_the_slot(org, receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    appt_id = book(client, patient, doctor, start="10:00").data["id"]
    later = tomorrow() + timedelta(days=1)
    res = client.post(f"{URL}{appt_id}/reschedule/", {"date": str(later), "start_time": "12:00"}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["date"] == str(later) and res.data["start_time"] == "12:00:00"
    assert res.data["reschedule_count"] == 1
    assert "moved" in res.data["notification"]["message"]
    other = make_patient(org, mobile="9876500000")
    assert book(client, other, doctor, start="10:00").status_code == 201  # old slot is free again
    log = AuditLog.objects.filter(action="update", object_id=appt_id).latest("created_at")
    assert log.changes["start_time"] == {"from": "10:00", "to": "12:00"}


@pytest.mark.django_db
def test_whatsapp_link_action(org, receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    appt_id = book(client, patient, doctor).data["id"]
    res = client.post(f"{URL}{appt_id}/whatsapp/")
    assert res.status_code == 200
    assert res.data["whatsapp_link"].startswith("https://wa.me/91")
    assert res.data["sms_sent"] is False
    assert AuditLog.objects.filter(action="share", object_id=appt_id).exists()


def test_whatsapp_number_format():
    assert whatsapp_number("98123 45678") == "919812345678"
    assert whatsapp_number("09812345678") == "919812345678"
    assert whatsapp_number("+91 98123-45678") == "919812345678"


# --- Queue ------------------------------------------------------------------------
@pytest.mark.django_db
def test_queue_groups_by_doctor(org, receptionist, doctor, branch_a, patient):
    client = client_for(receptionist, branch_a)
    client.post(URL, {"patient": str(patient.id), "doctor": str(doctor.id), "kind": "walk_in"}, format="json")
    other = make_patient(org, mobile="9876500000", first="Sunita", last="Shah")
    second = client.post(URL, {"patient": str(other.id), "doctor": str(doctor.id), "kind": "walk_in"},
                         format="json").data
    client_for(doctor, branch_a).post(f"{URL}{second['id']}/start/")
    res = client.get(URL + "queue/")
    assert res.status_code == 200
    group = res.data["doctors"][0]
    assert [w["token_number"] for w in group["waiting"]] == [1]
    assert group["now"][0]["display_name"] == "Sunita S."


# --- Who can do what -----------------------------------------------------------------
@pytest.mark.django_db
def test_therapist_can_view_but_not_book(therapist, doctor, branch_a, schedule, patient):
    client = client_for(therapist, branch_a)
    assert client.get(URL).status_code == 200
    assert book(client, patient, doctor).status_code == 403


@pytest.mark.django_db
def test_pharmacist_cannot_see_appointments(pharmacist, branch_a):
    assert client_for(pharmacist, branch_a).get(URL).status_code == 403


@pytest.mark.django_db
def test_appointments_stay_in_their_branch(receptionist, doctor, branch_a, branch_b, schedule, patient):
    book(client_for(receptionist, branch_a), patient, doctor)
    assert client_for(doctor, branch_a).get(URL).data["count"] == 1
    assert client_for(doctor, branch_b).get(URL).data["count"] == 0


@pytest.mark.django_db
def test_module_switched_off(org, receptionist, branch_a):
    BranchFeatureFlag.objects.create(organization=org, branch=branch_a, code="appointments", enabled=False)
    res = client_for(receptionist, branch_a).get(URL)
    assert res.status_code == 403 and "switched off" in str(res.data)


@pytest.mark.django_db
def test_appointments_are_never_deleted(receptionist, doctor, branch_a, schedule, patient):
    client = client_for(receptionist, branch_a)
    appt_id = book(client, patient, doctor).data["id"]
    assert client.delete(f"{URL}{appt_id}/").status_code == 405
