from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.common.models import MasterValue
from apps.patients.models import ConsentPurpose, Patient, PatientConsent
from conftest import client_for

URL = "/api/v1/patients/"
YY = timezone.localdate().year % 100


def master(org, category, code):
    return str(MasterValue.objects.get(organization=org, category=category, code=code).id)


def register(client, **extra):
    payload = {"first_name": "Test", "last_name": "Patient", "gender": "female", "age": 40, "mobile": "9876543210"}
    payload.update(extra)
    return client.post(URL, payload, format="json")


# --- Patient ID ----------------------------------------------------------------
@pytest.mark.django_db
def test_uhid_is_year_plus_running_number(receptionist, branch_a, org):
    client = client_for(receptionist, branch_a)
    first = register(client).data["uhid"]
    second = register(client, mobile="9876500000").data["uhid"]
    assert first == f"AY{YY:02d}-000001"
    assert second == f"AY{YY:02d}-000002"
    org.uhid_prefix = "SV"
    org.save()
    assert register(client, mobile="9876500001").data["uhid"] == f"SV{YY:02d}-000003"


@pytest.mark.django_db
def test_registration_needs_a_branch_and_valid_data(receptionist, branch_a):
    assert register(client_for(receptionist)).status_code == 400  # no branch chosen
    client = client_for(receptionist, branch_a)
    assert "mobile" in register(client, mobile="12345").data
    response = register(client, age=None)
    assert response.status_code == 400 and "date_of_birth" in response.data
    assert "pincode" in register(client, pincode="12").data


@pytest.mark.django_db
def test_age_becomes_estimated_date_of_birth(receptionist, branch_a):
    data = register(client_for(receptionist, branch_a), age=30).data
    assert data["dob_is_estimated"] is True
    assert data["age_years"] in (29, 30)
    exact = register(client_for(receptionist, branch_a), age=None, date_of_birth="1990-01-15", mobile="9876500002").data
    assert exact["dob_is_estimated"] is False


@pytest.mark.django_db
def test_mobile_is_cleaned(receptionist, branch_a):
    data = register(client_for(receptionist, branch_a), mobile="+91 98765-43210").data
    assert data["mobile"] == "9876543210"


@pytest.mark.django_db
def test_patients_are_never_deleted(org_admin, receptionist, branch_a):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    assert client_for(org_admin, branch_a).delete(f"{URL}{patient_id}/").status_code == 405


# --- Who sees what ---------------------------------------------------------------
@pytest.mark.django_db
def test_patient_registered_in_one_branch_is_seen_in_another(receptionist, doctor, branch_a, branch_b):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    response = client_for(doctor, branch_b).get(f"{URL}{patient_id}/")
    assert response.status_code == 200
    assert response.data["registered_branch_name"] == "Branch A"


@pytest.mark.django_db
def test_medical_history_hidden_from_receptionist_but_allergies_shown(receptionist, doctor, pharmacist, branch_a, org):
    payload = {
        "past_history": "Typhoid in 2010",
        "conditions": [{"condition": master(org, "medical_condition", "diabetes"), "since": "2015"}],
        "allergies": [{"allergen": "Sulfa", "allergy_type": master(org, "allergy_type", "drug"), "severity": "severe"}],
        "medications": [{"name": "Metformin", "dose": "500 mg", "frequency": "Twice a day"}],
    }
    patient_id = register(client_for(receptionist, branch_a), **payload).data["id"]

    reception_view = client_for(receptionist, branch_a).get(f"{URL}{patient_id}/").data
    assert reception_view["medical_history_hidden"] is True
    assert "past_history" not in reception_view and "conditions" not in reception_view
    assert reception_view["allergies"][0]["allergen"] == "Sulfa"

    pharmacist_view = client_for(pharmacist, branch_a).get(f"{URL}{patient_id}/").data
    assert "past_history" not in pharmacist_view

    doctor_view = client_for(doctor, branch_a).get(f"{URL}{patient_id}/").data
    assert doctor_view["past_history"] == "Typhoid in 2010"
    assert doctor_view["conditions"][0]["condition"]["code"] == "diabetes"
    assert doctor_view["medications"][0]["name"] == "Metformin"


@pytest.mark.django_db
def test_receptionist_cannot_change_medical_history_later(receptionist, doctor, branch_a):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    denied = client_for(receptionist, branch_a).patch(f"{URL}{patient_id}/", {"past_history": "x"}, format="json")
    assert denied.status_code == 400
    allowed = client_for(doctor, branch_a).patch(f"{URL}{patient_id}/", {"past_history": "Old fracture"}, format="json")
    assert allowed.status_code == 200


@pytest.mark.django_db
def test_history_is_encrypted_in_the_database_and_hidden_in_audit(receptionist, branch_a):
    patient_id = register(client_for(receptionist, branch_a), past_history="Secret note").data["id"]
    with connection.cursor() as cursor:
        cursor.execute("SELECT past_history FROM patients_patient WHERE id = %s", [patient_id.replace("-", "")])
        raw = cursor.fetchone()[0]
    assert raw.startswith("enc:") and "Secret" not in raw
    assert Patient.objects.get(pk=patient_id).past_history == "Secret note"
    log = AuditLog.objects.get(action="create", object_id=patient_id)
    assert "Secret" not in str(log.changes)


@pytest.mark.django_db
def test_editing_child_rows_updates_and_removes(doctor, branch_a, org):
    client = client_for(doctor, branch_a)
    created = register(client, medications=[{"name": "A"}, {"name": "B"}]).data
    keep = next(m for m in created["medications"] if m["name"] == "A")
    keep["dose"] = "10 mg"
    updated = client.patch(f"{URL}{created['id']}/", {"medications": [keep, {"name": "C"}]}, format="json").data
    assert sorted((m["name"], m["dose"]) for m in updated["medications"]) == [("A", "10 mg"), ("C", "")]


# --- List, search, audit ----------------------------------------------------------
@pytest.mark.django_db
def test_list_masks_phone_and_search_is_audited(receptionist, branch_a):
    client = client_for(receptionist, branch_a)
    register(client, first_name="Ramesh", last_name="Patel", mobile="9812345621")
    register(client, first_name="Sita", last_name="Shah", mobile="9800000000")
    rows = client.get(URL).data["results"]
    assert {r["mobile_masked"] for r in rows} == {"98XXXXXX21", "98XXXXXX00"}
    assert "mobile" not in rows[0]

    assert [r["first_name"] for r in client.get(URL, {"q": "ramesh pat"}).data["results"]] == ["Ramesh"]
    assert [r["first_name"] for r in client.get(URL, {"q": "45621"}).data["results"]] == ["Ramesh"]
    assert [r["first_name"] for r in client.get(URL, {"q": f"AY{YY:02d}-000002"}).data["results"]] == ["Sita"]
    assert AuditLog.objects.filter(action="view", object_type="patients.search").count() == 3


@pytest.mark.django_db
def test_every_view_is_audited(receptionist, doctor, branch_a):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    client_for(doctor, branch_a).get(f"{URL}{patient_id}/")
    log = AuditLog.objects.get(action="view", object_id=patient_id)
    assert log.user == doctor and log.branch == branch_a


@pytest.mark.django_db
def test_duplicate_check(receptionist, branch_a):
    client = client_for(receptionist, branch_a)
    register(client, first_name="Ramesh", last_name="Patel", mobile="9812345621")
    by_mobile = client.get(f"{URL}duplicates/", {"mobile": "9812345621"}).data
    by_name = client.get(f"{URL}duplicates/", {"first_name": "ramesh", "last_name": "PATEL"}).data
    assert len(by_mobile) == 1 and by_mobile[0]["mobile_masked"] == "98XXXXXX21"
    assert len(by_name) == 1
    assert client.get(f"{URL}duplicates/", {"mobile": "9000000000"}).data == []


@pytest.mark.django_db
def test_activity_needs_audit_permission(receptionist, branch_admin, branch_a):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    assert client_for(receptionist, branch_a).get(f"{URL}{patient_id}/activity/").status_code == 403
    activity = client_for(branch_admin, branch_a).get(f"{URL}{patient_id}/activity/").data
    assert any(row["action"] == "create" for row in activity)


# --- Vitals ------------------------------------------------------------------------
@pytest.mark.django_db
def test_vitals_bmi_and_permissions(receptionist, therapist, doctor, branch_a):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    payload = {"patient": patient_id, "weight_kg": "70", "height_cm": "175", "bp_systolic": 120, "bp_diastolic": 80}
    response = client_for(receptionist, branch_a).post("/api/v1/patient-vitals/", payload, format="json")
    assert response.status_code == 201
    assert response.data["bmi"] == "22.9"
    assert client_for(therapist, branch_a).post("/api/v1/patient-vitals/", payload, format="json").status_code == 403
    bad = client_for(doctor, branch_a).post("/api/v1/patient-vitals/", {**payload, "pulse": 400}, format="json")
    assert bad.status_code == 400
    rows = client_for(doctor, branch_a).get("/api/v1/patient-vitals/", {"patient": patient_id}).data
    assert len(rows) == 1 and rows[0]["branch_name"] == "Branch A"


# --- Documents ---------------------------------------------------------------------
@pytest.mark.django_db
def test_document_upload_checks_and_private_download(receptionist, doctor, branch_a):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    pdf = SimpleUploadedFile("report.pdf", b"%PDF-1.4 demo report", content_type="application/pdf")
    response = client_for(receptionist, branch_a).post(
        "/api/v1/patient-documents/", {"patient": patient_id, "title": "Blood test", "file": pdf}, format="multipart",
    )
    assert response.status_code == 201, response.data
    document_id = response.data["id"]

    fake = SimpleUploadedFile("virus.pdf", b"MZ not a pdf", content_type="application/pdf")
    bad = client_for(receptionist, branch_a).post(
        "/api/v1/patient-documents/", {"patient": patient_id, "title": "x", "file": fake}, format="multipart",
    )
    assert bad.status_code == 400
    exe = SimpleUploadedFile("tool.exe", b"MZ", content_type="application/octet-stream")
    assert client_for(receptionist, branch_a).post(
        "/api/v1/patient-documents/", {"patient": patient_id, "title": "x", "file": exe}, format="multipart",
    ).status_code == 400

    # Receptionist uploaded it but cannot open reports (needs emr.view)
    assert client_for(receptionist, branch_a).get(f"/api/v1/patient-documents/{document_id}/file/").status_code == 403
    download = client_for(doctor, branch_a).get(f"/api/v1/patient-documents/{document_id}/file/?download=1")
    assert download.status_code == 200
    assert b"".join(download.streaming_content).startswith(b"%PDF")
    assert AuditLog.objects.filter(action="export", object_id=document_id, user=doctor).exists()


# --- Consent -----------------------------------------------------------------------
@pytest.mark.django_db
def test_consent_grant_withdraw_and_history(receptionist, branch_a, org):
    patient_id = register(client_for(receptionist, branch_a)).data["id"]
    client = client_for(receptionist, branch_a)
    purpose = ConsentPurpose.objects.get(organization=org, code="communication")
    common = {"patient": patient_id, "purpose": str(purpose.id), "method": "verbal", "language": "gu"}
    assert client.post("/api/v1/patient-consents/", {**common, "granted": True}, format="json").status_code == 201
    assert client.post("/api/v1/patient-consents/", {**common, "granted": False}, format="json").status_code == 201

    status = {row["purpose"]["code"]: row["granted"] for row in
              client.get("/api/v1/patient-consents/status/", {"patient": patient_id}).data}
    assert status["communication"] is False
    assert status["research"] is None  # never asked
    history = client.get("/api/v1/patient-consents/", {"patient": patient_id}).data
    assert len(history) == 2

    record = PatientConsent.objects.first()
    with pytest.raises(PermissionError):
        record.save()
    with pytest.raises(PermissionError):
        record.delete()


@pytest.mark.django_db
def test_consent_purposes_have_three_languages(receptionist, branch_a):
    purposes = client_for(receptionist, branch_a).get("/api/v1/consent-purposes/").data
    assert {p["code"] for p in purposes} == {"treatment", "communication", "ai_processing", "research"}
    assert all(p["title_gu"] and p["description_hi"] for p in purposes)


@pytest.mark.django_db
def test_masters_list_and_only_admins_edit(receptionist, org_admin, branch_a):
    titles = client_for(receptionist, branch_a).get("/api/v1/masters/", {"category": "title"}).data
    assert "mrs" in {t["code"] for t in titles}
    payload = {"category": "title", "code": "prof", "label": "Prof"}
    assert client_for(receptionist, branch_a).post("/api/v1/masters/", payload, format="json").status_code == 403
    assert client_for(org_admin, branch_a).post("/api/v1/masters/", payload, format="json").status_code == 201


@pytest.mark.django_db
def test_other_organization_patient_is_invisible(org_admin, branch_a, roles):
    from apps.organizations.models import Organization

    other = Organization.objects.create(name="Other")
    stranger = Patient.objects.create(organization=other, uhid="X26-000001", first_name="X", gender="male",
                                      mobile="9800000009", date_of_birth=date(1990, 1, 1))
    assert client_for(org_admin, branch_a).get(f"{URL}{stranger.id}/").status_code == 404
