"""Additional setting "Bill therapy sessions automatically": a finished session goes on the patient's OPD bill."""
from datetime import date
from decimal import Decimal

import pytest

from apps.billing.models import Invoice, ServiceCharge
from apps.organizations.models import BranchFeatureFlag, OrganizationFeature, Room
from apps.patients.models import Patient
from apps.therapy.services import load_sample_therapies
from apps.therapy.models import TherapyType
from conftest import client_for

TODAY = date.today()


def _setup(org, branch_a, auto_bill):
    BranchFeatureFlag.objects.update_or_create(branch=branch_a, code="panchakarma",
                                               defaults={"organization": org, "enabled": True})
    if auto_bill:
        OrganizationFeature.objects.update_or_create(organization=org, code="therapy_auto_billing",
                                                     defaults={"enabled": True})


@pytest.fixture
def patient(org):
    return Patient.objects.create(organization=org, uhid="9", first_name="Kiran", last_name="Shah", gender="female",
                                  mobile="9876500009")


@pytest.fixture
def abhyanga(org):
    load_sample_therapies(org)
    therapy = TherapyType.objects.get(organization=org, name__startswith="Abhyanga")
    therapy.service = ServiceCharge.objects.create(organization=org, name="Abhyanga session", price=Decimal("500"))
    therapy.save()
    return therapy


def _plan(client, patient, therapy):
    return client.post("/api/v1/therapy-plans/", {
        "patient": str(patient.id), "title": "Course", "start_date": str(TODAY),
        "items": [{"therapy": str(therapy.id), "stage": "purva", "sessions_planned": 3}]}, format="json").data


def _book(client, plan, therapist, start="10:00"):
    made = client.post(f"/api/v1/therapy-plans/{plan['id']}/schedule/", {
        "item": plan["items"][0]["id"], "dates": [str(TODAY)], "start_time": start,
        "therapist": str(therapist.id)}, format="json")
    assert made.status_code == 201, made.data
    return made.data[0]["id"]


def _session(client, patient, therapy, therapist):
    return _book(client, _plan(client, patient, therapy), therapist)


@pytest.mark.django_db
def test_switch_is_off_by_default_and_nothing_is_billed(org, roles, branch_a, doctor, therapist, patient, abhyanga):
    _setup(org, branch_a, auto_bill=False)
    sid = _session(client_for(doctor, branch_a), patient, abhyanga, therapist)
    assert client_for(therapist, branch_a).post(f"/api/v1/therapy-sessions/{sid}/complete/", {}, format="json").status_code == 200
    assert Invoice.objects.count() == 0


@pytest.mark.django_db
def test_finished_session_is_added_to_the_patients_opd_bill(org, roles, branch_a, doctor, therapist, patient, abhyanga):
    _setup(org, branch_a, auto_bill=True)
    sid = _session(client_for(doctor, branch_a), patient, abhyanga, therapist)
    res = client_for(therapist, branch_a).post(f"/api/v1/therapy-sessions/{sid}/complete/", {}, format="json")
    assert res.status_code == 200
    invoice = Invoice.objects.get()
    assert invoice.series == "OP" and invoice.patient_id == patient.id and invoice.total_amount == Decimal("500")
    assert "Abhyanga" in invoice.lines.get().description


@pytest.mark.django_db
def test_second_session_the_same_day_goes_on_the_same_bill_and_undo_redo_does_not_double_bill(
        org, roles, branch_a, doctor, therapist, patient, abhyanga):
    _setup(org, branch_a, auto_bill=True)
    c = client_for(doctor, branch_a)
    plan = _plan(c, patient, abhyanga)
    first = _book(c, plan, therapist)
    t = client_for(therapist, branch_a)
    t.post(f"/api/v1/therapy-sessions/{first}/complete/", {}, format="json")
    # undo (goes back a step) and finish again: still one line
    c.post(f"/api/v1/therapy-sessions/{first}/undo/", {}, format="json")
    t.post(f"/api/v1/therapy-sessions/{first}/complete/", {}, format="json")
    assert Invoice.objects.count() == 1 and Invoice.objects.get().lines.count() == 1
    # a different session of the same patient the same day is added to that bill
    second = _book(c, plan, therapist, start="14:00")
    t.post(f"/api/v1/therapy-sessions/{second}/complete/", {}, format="json")
    invoice = Invoice.objects.get()
    assert invoice.lines.count() == 2 and invoice.total_amount == Decimal("1000")


@pytest.mark.django_db
def test_therapy_without_a_price_is_not_billed(org, roles, branch_a, doctor, therapist, patient, abhyanga):
    _setup(org, branch_a, auto_bill=True)
    abhyanga.service = None
    abhyanga.save()
    sid = _session(client_for(doctor, branch_a), patient, abhyanga, therapist)
    assert client_for(therapist, branch_a).post(f"/api/v1/therapy-sessions/{sid}/complete/", {}, format="json").status_code == 200
    assert Invoice.objects.count() == 0


# --- WhatsApp reminder for a therapy session (Additional settings -> "WhatsApp reminders") ---
def _reminders(org, on=True):
    OrganizationFeature.objects.update_or_create(organization=org, code="whatsapp_reminders", defaults={"enabled": on})


def _consent(org, patient, branch):
    from apps.patients.models import ConsentPurpose, PatientConsent
    purpose = ConsentPurpose.objects.get(organization=org, code="communication")
    PatientConsent.objects.create(organization=org, patient=patient, branch=branch, purpose=purpose,
                                  purpose_version=purpose.version, granted=True, method="verbal", language="en")


@pytest.mark.django_db
def test_therapy_whatsapp_reminder_needs_the_switch_and_consent(org, roles, branch_a, doctor, therapist, patient, abhyanga):
    _setup(org, branch_a, auto_bill=False)
    patient.preferred_language = "en"
    patient.save()
    c = client_for(doctor, branch_a)
    sid = _session(c, patient, abhyanga, therapist)
    assert c.post(f"/api/v1/therapy-sessions/{sid}/whatsapp/").status_code == 403  # switch is off
    _reminders(org)
    assert c.post(f"/api/v1/therapy-sessions/{sid}/whatsapp/").data["consent"] is False  # no consent given
    _consent(org, patient, branch_a)
    res = c.post(f"/api/v1/therapy-sessions/{sid}/whatsapp/")
    assert res.data["consent"] is True and res.data["whatsapp_link"].startswith("https://wa.me/919876500009?text=")
    assert "Abhyanga" in res.data["message"] and "10:00 AM" in res.data["message"]


@pytest.mark.django_db
def test_therapy_reminder_uses_the_gujarati_therapy_name_for_a_gujarati_patient(org, roles, branch_a, doctor, therapist, patient, abhyanga):
    _setup(org, branch_a, auto_bill=False)
    _reminders(org)
    patient.preferred_language = "gu"
    patient.save()
    _consent(org, patient, branch_a)
    c = client_for(doctor, branch_a)
    sid = _session(c, patient, abhyanga, therapist)
    message = c.post(f"/api/v1/therapy-sessions/{sid}/whatsapp/").data["message"]
    assert abhyanga.name_gu in message and "યાદ" in message


# --- Setting a therapy's price straight from the Therapies screen ---
@pytest.mark.django_db
def test_setting_a_price_on_a_therapy_creates_and_links_its_service(org, roles, branch_a, doctor, therapist, abhyanga):
    _setup(org, branch_a, auto_bill=False)
    abhyanga.service = None
    abhyanga.save()
    c = client_for(doctor, branch_a)
    res = c.patch(f"/api/v1/therapies/{abhyanga.id}/", {"set_price": "650"}, format="json")
    assert res.status_code == 200, res.data
    abhyanga.refresh_from_db()
    assert abhyanga.service is not None and abhyanga.service.price == Decimal("650")
    assert abhyanga.service.name == abhyanga.name and res.data["price"] == "650.00"
    # a second time with a price already linked does not create another service
    before = ServiceCharge.objects.count()
    c.patch(f"/api/v1/therapies/{abhyanga.id}/", {"set_price": "700"}, format="json")
    assert ServiceCharge.objects.count() == before
