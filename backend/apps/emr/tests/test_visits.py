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


# --- Step 4 additions: symptom scores, photos, editable templates -------------------------
def png_file(name="photo.png"):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.mark.django_db
def test_symptom_score_and_progress(doctor, branch_a, appointment, patient):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    res = client.patch(f"{URL}{visit_id}/", {"complaints": [{"label": "Knee pain", "score": 7}]}, format="json")
    assert res.data["complaints"][0]["score"] == 7
    assert client.patch(f"{URL}{visit_id}/", {"complaints": [{"label": "Knee pain", "score": 11}]},
                        format="json").status_code == 400
    timeline = client.get(URL, {"patient": patient.id}).data["results"]
    assert timeline[0]["scores"] == {"Knee pain": 7}


@pytest.mark.django_db
def test_future_appointment_cannot_open_checkup(org, doctor, branch_a, patient):
    from datetime import timedelta

    later = Appointment.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                       date=timezone.localdate() + timedelta(days=2), start_time=time(11, 0))
    res = start(client_for(doctor, branch_a), later)
    assert res.status_code == 400 and "later date" in str(res.data)


@pytest.mark.django_db
def test_before_after_photos(doctor, branch_a, appointment, patient, receptionist):
    client = client_for(doctor, branch_a)
    visit_id = start(client, appointment).data["id"]
    res = client.post(f"{URL}{visit_id}/photos/", {"file": png_file(), "kind": "before", "caption": "Left knee"},
                      format="multipart")
    assert res.status_code == 201, res.data
    photo_id = res.data["id"]
    file_res = client.get(f"{URL}{visit_id}/photos/{photo_id}/file/")
    assert file_res.status_code == 200 and file_res["Content-Type"] == "image/png"
    assert AuditLog.objects.filter(action="view", object_id=photo_id).exists()
    assert len(client.get(URL + "patient-photos/", {"patient": patient.id}).data) == 1
    fake = client.post(f"{URL}{visit_id}/photos/",
                       {"file": png_file("x.png").__class__("x.png", b"not an image", content_type="image/png")},
                       format="multipart")
    assert fake.status_code == 400
    assert client_for(receptionist, branch_a).get(f"{URL}{visit_id}/photos/{photo_id}/file/").status_code == 403
    assert client.delete(f"{URL}{visit_id}/photos/{photo_id}/").status_code == 204
    assert client.get(URL + "patient-photos/", {"patient": patient.id}).data == []


@pytest.mark.django_db
def test_admin_edits_template_and_old_visits_keep_old_questions(doctor, branch_admin, branch_a, appointment, templates):
    tpl = templates["ashtavidha"]
    visit_id = start(client_for(doctor, branch_a), appointment).data["id"]
    client_for(doctor, branch_a).put(f"{URL}{visit_id}/exams/ashtavidha/", {"values": {"nadi": "vata"}}, format="json")

    admin = client_for(branch_admin, branch_a)
    fields = tpl.fields + [{"key": "agni_note", "type": "text", "label": {"en": "Agni note"}}]
    res = admin.patch(f"/api/v1/exam-templates/{tpl.id}/", {"fields": fields}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["version"] == 2 and res.data["fields"][-1]["key"] == "agni_note"

    exam = client_for(doctor, branch_a).get(f"{URL}{visit_id}/").data["exams"][0]
    assert exam["template_version"] == 1
    assert [f["key"] for f in exam["template_fields"]] == [f["key"] for f in tpl.fields]  # old questions


@pytest.mark.django_db
def test_template_rules(doctor, branch_admin, branch_a, templates):
    admin = client_for(branch_admin, branch_a)
    url = "/api/v1/exam-templates/"
    # A doctor cannot change templates
    assert client_for(doctor, branch_a).post(url, {"name": "X", "fields": []}, format="json").status_code == 403
    # Questionnaire answers must count for a dosha
    bad = admin.post(url, {"name": "My Prakriti", "kind": "questionnaire", "fields": [
        {"key": "q1", "label": {"en": "Q1"}, "options": [{"value": "fast", "label": {"en": "Fast"}}]}]}, format="json")
    assert bad.status_code == 400
    good = admin.post(url, {"name": "Nadi detail", "fields": [
        {"key": "rate", "type": "number", "unit": "/min", "label": {"en": "Rate", "gu": "દર"}}]}, format="json")
    assert good.status_code == 201 and good.data["code"] == "nadi_detail"
    # Switched-off templates are hidden from the check-up screen
    admin.patch(f"{url}{good.data['id']}/", {"is_active": False}, format="json")
    codes = [t["code"] for t in client_for(doctor, branch_a).get(url).data]
    assert "nadi_detail" not in codes
