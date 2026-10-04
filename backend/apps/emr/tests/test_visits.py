from datetime import time

import pytest
from django.db import connection
from django.utils import timezone

from apps.appointments.models import Appointment
from apps.audit.models import AuditLog
from apps.emr.models import ExamTemplate, Visit
from apps.emr.services import ensure_exam_templates
from apps.patients.models import Patient
from conftest import client_for

URL = "/api/v1/visits/"


@pytest.fixture
def patient(org, roles):
    return Patient.objects.create(organization=org, uhid="T-1", first_name="Ramesh", last_name="Patel",
                                  gender="male", mobile="9876543210")


@pytest.fixture
def templates(org, roles):
    ensure_exam_templates(org)  # (roles fixture already runs ensure_defaults; this is a no-op then)
    return {t.code: t for t in ExamTemplate.objects.filter(organization=org)}


@pytest.fixture
def appointment(org, branch_a, patient, doctor):
    return Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                      date=timezone.localdate(), start_time=time(10, 0), end_time=time(10, 15))


def start(client, appointment):
    return client.post(URL, {"appointment": str(appointment.id)}, format="json")


@pytest.mark.django_db
def test_starting_templates_exist(templates):
    assert set(templates) == {"ashtavidha", "dashavidha", "agni_habits", "prakriti"}
    assert templates["prakriti"].kind == "questionnaire"


@pytest.mark.django_db
def test_open_visit_from_appointment(doctor, branch_a, appointment):
    client = client_for(doctor, branch_a)
    res = start(client, appointment)
    assert res.status_code == 201, res.data
    appointment.refresh_from_db()
    assert appointment.status == "in_consultation" and appointment.token_number == 1
    again = start(client, appointment)  # opening again returns the same visit
    assert again.status_code == 200 and again.data["id"] == res.data["id"]


@pytest.mark.django_db
def test_save_sections_and_complete(doctor, branch_a, appointment):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    res = client.patch(f"{URL}{visit_id}/", {
        "complaints": [{"label": "Knee pain", "duration": 3, "duration_unit": "months", "severity": "moderate"}],
        "history_notes": "Pain worse in the morning",
        "diagnoses": [{"label": "Sandhivata (Osteoarthritis)", "kind": "provisional", "system": "namaste", "code": "SR-1"}],
        "advice": ["Warm water", ""],
        "follow_up_date": str(timezone.localdate()),
    }, format="json")
    assert res.status_code == 200, res.data
    assert res.data["complaints"][0]["duration"] == 3
    assert res.data["advice"] == ["Warm water"]
    res = client.post(f"{URL}{visit_id}/complete/")
    assert res.data["status"] == "completed"
    appointment.refresh_from_db()
    assert appointment.status == "completed"


@pytest.mark.django_db
def test_notes_are_encrypted_and_not_in_audit_log(doctor, branch_a, appointment):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    client.patch(f"{URL}{visit_id}/", {"history_notes": "Secret history", "complaints": [{"label": "Knee pain"}]},
                 format="json")
    with connection.cursor() as cursor:
        cursor.execute("SELECT history_notes, complaints FROM emr_visit WHERE id = %s", [visit_id.replace("-", "")
                       if connection.vendor == "sqlite" else visit_id])
        raw = cursor.fetchone()
    assert raw[0].startswith("enc:") and raw[1].startswith("enc:")
    assert "Knee" not in raw[1]
    log = AuditLog.objects.filter(action="update", object_id=visit_id).latest("created_at")
    assert log.changes["history_notes"] == "changed"


@pytest.mark.django_db
def test_wrong_section_data_refused(doctor, branch_a, appointment):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    assert client.patch(f"{URL}{visit_id}/", {"complaints": [{"label": ""}]}, format="json").status_code == 400
    assert client.patch(f"{URL}{visit_id}/", {"diagnoses": [{"label": "X", "kind": "maybe"}]},
                        format="json").status_code == 400


@pytest.mark.django_db
def test_ashtavidha_answers_are_checked(doctor, branch_a, appointment, templates):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    url = f"{URL}{visit_id}/exams/ashtavidha/"
    ok = client.put(url, {"values": {"nadi": "vata", "nadi_rate": "78", "unknown": "x"}}, format="json")
    assert ok.status_code == 200, ok.data
    assert ok.data["values"] == {"nadi": "vata", "nadi_rate": 78}
    bad = client.put(url, {"values": {"nadi": "fast"}}, format="json")
    assert bad.status_code == 400
    assert client.put(url, {"values": {"nadi_rate": 500}}, format="json").status_code == 400


@pytest.mark.django_db
def test_prakriti_score(doctor, branch_a, appointment, templates):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    keys = [f["key"] for f in templates["prakriti"].fields]
    answers = {k: "vata" for k in keys[:7]}
    answers.update({k: "pitta" for k in keys[7:10]})
    answers.update({k: "kapha" for k in keys[10:]})
    res = client.put(f"{URL}{visit_id}/exams/prakriti/", {"values": answers}, format="json")
    result = res.data["result"]
    assert result["vata"] == 58 and result["pitta"] == 25 and result["kapha"] == 17
    assert result["type"] == "vata"
    visit = client.get(f"{URL}{visit_id}/").data
    assert visit["prakriti"]["type"] == "vata"  # shown in the patient header from now on


@pytest.mark.django_db
def test_history_from_all_branches(org, doctor, branch_a, branch_b, patient):
    Visit.objects.create(organization=org, branch=branch_b, patient=patient, doctor=doctor,
                         visit_date=timezone.localdate())
    res = client_for(doctor, branch_a).get(URL, {"patient": patient.id})
    assert res.data["count"] == 1 and res.data["results"][0]["branch_name"] == "Branch B"


@pytest.mark.django_db
def test_receptionist_cannot_see_checkups(receptionist, branch_a, patient):
    client = client_for(receptionist, branch_a)
    assert client.get(URL, {"patient": patient.id}).status_code == 403
    assert client.post(URL, {"patient": str(patient.id)}, format="json").status_code == 403


@pytest.mark.django_db
def test_opening_visit_is_audited(doctor, branch_a, appointment):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    client.get(f"{URL}{visit_id}/")
    assert AuditLog.objects.filter(action="view", object_id=visit_id).exists()


@pytest.mark.django_db
def test_doctor_can_start_without_appointment(doctor, branch_a, patient, org_admin):
    res = client_for(doctor, branch_a).post(URL, {"patient": str(patient.id)}, format="json")
    assert res.status_code == 201 and res.data["appointment"] is None
    res = client_for(org_admin, branch_a).post(URL, {"patient": str(patient.id)}, format="json")
    assert res.status_code == 400  # not a doctor
