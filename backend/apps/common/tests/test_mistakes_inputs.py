"""
"By mistake" tests, part 4: odd files, odd URLs, odd typing. Nothing here may crash the server (500) or leak data.
"""
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.patients.models import Patient
from conftest import client_for

API = "/api/v1/"


@pytest.fixture
def patient(org, roles):
    return Patient.objects.create(organization=org, uhid="1", first_name="Ramesh", last_name="Patel", gender="male",
                                  mobile="9876543210")


# ---------------------------------------------------------------- files
@pytest.mark.django_db
@pytest.mark.parametrize("name,content", [
    ("empty.csv", b""),
    ("garbage.csv", b"\x00\x01\x02\xff\xfe binary garbage"),
    ("wrong_columns.csv", b"foo,bar\n1,2\n"),
    ("not_excel.xlsx", b"this is not an excel file"),
    ("photo.jpg", b"\xff\xd8\xff not really a picture"),
])
def test_wrong_import_files_give_a_message_not_a_crash(org_admin, branch_a, roles, name, content):
    res = client_for(org_admin, branch_a).post(API + "medicines/import/", {"file": SimpleUploadedFile(name, content)},
                                               format="multipart")
    assert res.status_code in (200, 400), (name, res.status_code)
    if res.status_code == 200:
        assert res.data.get("created", 0) == 0  # nothing wrongly imported


@pytest.mark.django_db
def test_import_without_a_file_is_refused(org_admin, branch_a, roles):
    assert client_for(org_admin, branch_a).post(API + "medicines/import/", {}, format="multipart").status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("name,content", [
    ("big.pdf", b"%PDF-1.4\n" + b"0" * (26 * 1024 * 1024)),   # too big
    ("virus.exe", b"MZ\x90\x00"),
    ("fake.pdf", b"not a pdf at all"),
    ("empty.pdf", b""),
    ("script.html", b"<script>alert(1)</script>"),
])
def test_wrong_patient_uploads_are_refused(doctor, branch_a, patient, name, content):
    res = client_for(doctor, branch_a).post(API + "patient-documents/", {
        "patient": str(patient.id), "title": "Report", "file": SimpleUploadedFile(name, content)}, format="multipart")
    assert res.status_code == 400, (name, res.status_code)


@pytest.mark.django_db
def test_wrong_logo_files_are_refused(org_admin, branch_a):
    for name, content in (("logo.svg", b"<svg onload=alert(1)></svg>"), ("logo.exe", b"MZ"), ("logo.png", b"not png")):
        res = client_for(org_admin, branch_a).post(API + "organization/logo/", {"file": SimpleUploadedFile(name, content)},
                                                   format="multipart")
        assert res.status_code in (400, 415), (name, res.status_code, res.data)


# ---------------------------------------------------------------- odd URLs and values
@pytest.mark.django_db
@pytest.mark.parametrize("path", [
    "patients/?page=-1", "patients/?page=abc", "patients/?page=99999", "patients/?page_size=0", "patients/?page_size=100000",
    "patients/?ordering=;drop table", "patients/?ordering=password", "patients/?search=%27%20OR%201%3D1--",
    "patients/?search=" + "a" * 5000, "patients/?q=%00", "patients/?gender=zzz", "patients/?created_at__gte=notadate",
    "appointments/?date=31-02-2026", "appointments/?date=abc", "appointments/?doctor=not-a-uuid", "invoices/?status=zzz",
    "invoices/summary/?date=abc", "stock/?q=%27", "visits/?patient=not-a-uuid", "reports/zzz/", "reports/collection/?from=abc",
])
def test_odd_urls_never_crash_the_server(org_admin, branch_a, roles, path):
    res = client_for(org_admin, branch_a).get(API + path)
    assert res.status_code < 500, (path, res.status_code)
    assert "password" not in str(res.content).lower() or res.status_code != 200


@pytest.mark.django_db
@pytest.mark.parametrize("name", ["<script>alert(1)</script>", "Robert'); DROP TABLE patients;--", "ગુજરાતી નામ", "नाम हिंदी", "😀 Smile", "A" * 300])
def test_odd_names_are_saved_as_plain_text_or_refused(receptionist, branch_a, name):
    res = client_for(receptionist, branch_a).post(API + "patients/", {
        "first_name": name, "last_name": "Test", "gender": "male", "age": 30, "mobile": "9876500009"}, format="json")
    assert res.status_code in (201, 400), (name, res.status_code)
    if res.status_code == 201:
        assert res.data["first_name"] == name  # stored exactly as typed; the screen shows it as text, never as code
        assert Patient.objects.filter(first_name=name).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("body", ["not json at all", "[]", "null", '{"a": ', "123"])
def test_broken_request_bodies_never_crash(receptionist, branch_a, body):
    res = client_for(receptionist, branch_a).post(API + "patients/", data=body, content_type="application/json")
    assert res.status_code == 400, (body, res.status_code)


@pytest.mark.django_db
def test_documents_with_wrong_ids_or_kinds(doctor, branch_a):
    c = client_for(doctor, branch_a)
    assert c.get(API + "documents/prescription/11111111-1111-1111-1111-111111111111/").status_code == 404
    assert c.get(API + "documents/unknown/11111111-1111-1111-1111-111111111111/").status_code == 404
    assert c.get(API + "documents/prescription/not-a-uuid/").status_code == 404
    assert c.get(API + "invoices/11111111-1111-1111-1111-111111111111/pdf/").status_code == 404
    assert c.get(API + "invoices/not-a-uuid/").status_code == 404


@pytest.mark.django_db
def test_verify_page_with_wrong_token_does_not_leak(patient):
    c = APIClient()
    for token in ("nope", "A" * 200, "../../etc/passwd", "%00"):
        res = c.get(API + f"verify/{token}/")
        assert res.status_code in (404, 400), token
        assert "Ramesh" not in str(res.content)


@pytest.mark.django_db
def test_nothing_works_without_login_or_branch(org, roles, branch_a, receptionist):
    anonymous = APIClient()
    for path in ("patients/", "appointments/", "invoices/", "stock/", "visits/", "staff/", "audit-logs/", "therapy-plans/",
                 "print-settings/", "reports/collection/"):
        assert anonymous.get(API + path).status_code in (401, 403), path
    no_branch = client_for(receptionist)  # logged in but did not choose a branch
    for path in ("appointments/", "invoices/", "patients/"):
        assert no_branch.get(API + path).status_code in (400, 403), path


@pytest.mark.django_db
def test_expired_or_fake_token_is_refused(org, roles):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Bearer this.is.not.a.token")
    assert c.get(API + "patients/").status_code == 401
    assert c.get(API + "auth/me/").status_code == 401
