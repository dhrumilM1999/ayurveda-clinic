"""The "Patient Report" window of the check-up screen: what was written at the patient's visits between two dates."""
from datetime import date, time, timedelta

import pytest
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.emr.models import Visit
from apps.patients.models import Patient
from conftest import client_for

URL = "/api/v1/visits/report/"


@pytest.fixture
def patient(org, roles):
    return Patient.objects.create(organization=org, uhid="R-1", first_name="Meena", last_name="Shah", gender="female",
                                  mobile="9876500011")


def make_visit(org, branch, patient, doctor, day, **fields):
    return Visit.objects.create(organization=org, branch=branch, patient=patient, doctor=doctor, visit_date=day, **fields)


@pytest.mark.django_db
def test_report_lists_the_visits_in_the_dates_newest_first(org, roles, branch_a, doctor, patient):
    today = timezone.localdate()
    make_visit(org, branch_a, patient, doctor, today - timedelta(days=40), complaints=[{"label": "Old cough"}])
    make_visit(org, branch_a, patient, doctor, today - timedelta(days=5), complaints=[{"label": "Headache"}],
               diagnoses=[{"label": "Shirashool"}], advice=["Rest"], history_notes="Since a week")
    client = client_for(doctor, branch_a)
    res = client.get(URL, {"patient": str(patient.id), "from": str(today - timedelta(days=30)), "to": str(today)})
    assert res.status_code == 200, res.data
    assert [v["visit_date"] for v in res.data] == [str(today - timedelta(days=5))]
    visit = res.data[0]
    assert visit["complaints"] == ["Headache"] and visit["diagnoses"] == ["Shirashool"] and visit["advice"] == ["Rest"]
    assert visit["history_notes"] == "Since a week" and visit["doctor_name"]
    assert visit["rx"] == [] and visit["investigations"] == []


@pytest.mark.django_db
def test_report_needs_a_patient_and_valid_dates(org, roles, branch_a, doctor, patient):
    client = client_for(doctor, branch_a)
    assert client.get(URL).status_code == 400
    assert client.get(URL, {"patient": str(patient.id), "from": "not-a-date"}).status_code == 400
    assert client.get(URL, {"patient": str(patient.id), "from": "2026-10-10", "to": "2026-10-01"}).status_code == 400


@pytest.mark.django_db
def test_report_is_written_to_the_audit_log_and_hides_medical_text_from_it(org, roles, branch_a, doctor, patient):
    make_visit(org, branch_a, patient, doctor, timezone.localdate(), history_notes="secret history")
    client_for(doctor, branch_a).get(URL, {"patient": str(patient.id)})
    log = AuditLog.objects.filter(action="view", object_type__icontains="patient").order_by("-created_at").first()
    assert log is not None and "secret history" not in str(log.changes)


@pytest.mark.django_db
def test_someone_without_check_up_permission_cannot_open_the_report(org, roles, branch_a, receptionist, patient):
    assert client_for(receptionist, branch_a).get(URL, {"patient": str(patient.id)}).status_code == 403


@pytest.mark.django_db
def test_report_shows_the_medicines_and_tests_of_a_visit(org, roles, branch_a, doctor, patient):
    from apps.emr.models import VisitInvestigation
    from apps.prescriptions.models import Prescription, PrescriptionItem

    visit = make_visit(org, branch_a, patient, doctor, timezone.localdate())
    rx = Prescription.objects.create(organization=org, branch=branch_a, visit=visit, patient=patient, doctor=doctor)
    PrescriptionItem.objects.create(organization=org, prescription=rx, medicine_name="Triphala Churna", dose="3", dose_unit="gram",
                                    frequency="0-0-1", timing="After food", duration=15, duration_unit="days")
    VisitInvestigation.objects.create(organization=org, visit=visit, patient=patient, test_name="CBC", advised_on=visit.visit_date)
    data = client_for(doctor, branch_a).get(URL, {"patient": str(patient.id)}).data
    assert data[0]["rx"] == [{"medicine": "Triphala Churna", "dose": "3 gram", "frequency": "0-0-1", "timing": "After food",
                              "duration": "15 days"}]
    assert data[0]["investigations"] == [{"test": "CBC", "status": "advised"}]
