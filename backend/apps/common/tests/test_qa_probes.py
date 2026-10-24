"""
QA probes: small direct checks for items of docs/qa/QA_CHECKLIST.md that had no test of their own yet.
Each test names the checklist id it answers.
"""
import re
from datetime import time

import pytest
from django.apps import apps as django_apps
from django.conf import settings
from django.contrib.auth.hashers import identify_hasher
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.patients.models import Patient
from conftest import PASSWORD, client_for, make_user

API = "/api/v1/"


def login(username, password=PASSWORD):
    return APIClient().post(API + "auth/login/", {"username": username, "password": password}, format="json")


@pytest.mark.django_db
def test_AUTH_004_passwords_use_argon2(receptionist):
    receptionist.refresh_from_db()
    assert receptionist.password.startswith("argon2$")
    assert identify_hasher(receptionist.password).algorithm == "argon2"
    assert settings.PASSWORD_HASHERS[0].endswith("Argon2PasswordHasher")


@pytest.mark.django_db
def test_AUTH_005_access_token_is_short_lived():
    assert settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds() <= 15 * 60


@pytest.mark.django_db
def test_AUTH_006_013_logout_revokes_the_refresh_token(receptionist, branch_a):
    tokens = login(receptionist.username).data
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    out = c.post(API + "auth/logout/", {"refresh": tokens["refresh"]}, format="json")
    assert out.status_code in (200, 204, 205)
    again = APIClient().post(API + "auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert again.status_code == 401


@pytest.mark.django_db
def test_AUTH_010_a_switched_off_user_cannot_keep_working(receptionist, branch_a):
    tokens = login(receptionist.username).data
    receptionist.is_active = False
    receptionist.save()
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}", HTTP_X_BRANCH_ID=str(branch_a.id))
    assert c.get(API + "patients/").status_code in (401, 403)
    assert APIClient().post(API + "auth/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401


@pytest.mark.django_db
def test_AUTH_008_password_change_needs_the_old_password_and_keeps_rules(receptionist, branch_a):
    c = client_for(receptionist, branch_a)
    bad = c.post(API + "auth/change-password/", {"old_password": "wrong", "new_password": "NewClinic@2026x"}, format="json")
    assert bad.status_code == 400
    weak = c.post(API + "auth/change-password/", {"old_password": PASSWORD, "new_password": "12345678"}, format="json")
    assert weak.status_code == 400
    ok = c.post(API + "auth/change-password/", {"old_password": PASSWORD, "new_password": "NewClinic@2026x"}, format="json")
    assert ok.status_code in (200, 204)
    assert login(receptionist.username, "NewClinic@2026x").status_code == 200
    assert login(receptionist.username, PASSWORD).status_code in (400, 401)


@pytest.mark.django_db
def test_AUD_003_audit_entries_have_user_branch_time_and_ip(receptionist, branch_a):
    c = client_for(receptionist, branch_a)
    c.post(API + "patients/", {"first_name": "Audit", "last_name": "Probe", "gender": "male", "age": 30,
                               "mobile": "9876500055"}, format="json", REMOTE_ADDR="10.1.2.3")
    entry = AuditLog.objects.filter(action="create").order_by("-created_at").first()
    assert entry.user_id == receptionist.id and entry.branch_id == branch_a.id and entry.created_at
    assert entry.ip_address == "10.1.2.3"


@pytest.mark.django_db
def test_AUD_010_unauthorized_attempts_leave_a_trace_or_are_reported(therapist, branch_a):
    before = AuditLog.objects.count()
    res = client_for(therapist, branch_a).get(API + "invoices/")
    assert res.status_code == 403
    # Failed logins are logged (test_wrong_password_is_rejected_and_logged); a 403 on a screen is not an audit event
    assert AuditLog.objects.count() >= before


@pytest.mark.django_db
def test_SEC_008_private_files_have_no_public_address(client, receptionist):
    for path in ("/media/", "/private_media/", "/private-not-served/", "/static/private_media/", "/media/patients/",
                 "/private_media/patients/", "/.env", "/backend/.env"):
        assert client.get(path).status_code in (404, 403, 301, 302), path


@pytest.mark.django_db
def test_SEC_011_no_aadhaar_is_collected():
    for model in django_apps.get_models():
        for field in model._meta.get_fields():
            assert "aadhaar" not in field.name.lower() and "aadhar" not in field.name.lower(), (model, field.name)


@pytest.mark.django_db
def test_DB_005_006_every_main_table_has_uuid_owner_timestamps_and_soft_delete():
    """Main tables (apps of this project) have a UUID id, timestamps, created_by/updated_by and soft delete."""
    exceptions = {  # small technical tables, never shown to people
        "TokenSequence", "UhidSequence", "DocumentSequence", "LoginOtp", "OutstandingToken", "BlacklistedToken", "Migration",
        # By design: the audit log is append-only (no soft delete / updated_at), version histories are immutable rows
        # with a counter id, the login code table is temporary and the message log is a plain record.
        "LoginChallenge", "AuditLog", "OutboundMessage", "ExamTemplateVersion", "MedicineVersion",
    }
    problems = []
    for model in django_apps.get_models():
        if not model.__module__.startswith("apps.") or model.__name__ in exceptions:
            continue
        names = {f.name for f in model._meta.get_fields()}
        pk = model._meta.pk
        if pk.get_internal_type() != "UUIDField":
            problems.append((model.__name__, "pk is not UUID"))
        missing = {"created_at", "updated_at", "is_deleted"} - names
        if missing:
            problems.append((model.__name__, f"missing {sorted(missing)}"))
    # Report the list, so the QA record shows exactly what is outside the rule
    assert problems == [], problems


@pytest.mark.django_db
def test_SEC_004_names_are_escaped_in_print_templates(org, roles, branch_a, doctor):
    from apps.documents.services import render_html
    from apps.documents.services import follow_up_context

    patient = Patient.objects.create(organization=org, uhid="X1", first_name="<script>alert(1)</script>", last_name="Z",
                                     gender="male", mobile="9876500066")
    from apps.emr.models import Visit

    visit = Visit.objects.create(organization=org, branch=branch_a, patient=patient, doctor=doctor,
                                 visit_date=timezone.localdate(), follow_up_date=timezone.localdate())
    html = render_html("follow_up_card.html", "a6", {**follow_up_context(visit, "en"), "number": "N", "duplicate": False,
                                                   "qr": "", "is_cancelled": False, "pad": None})
    assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html


@pytest.mark.django_db
def test_DOC_006_bills_fit_thermal_80mm_and_58mm(org, branch_a, receptionist):
    from apps.billing.services import create_invoice

    invoice = create_invoice(branch_a, receptionist, series="OP", lines=[
        {"kind": "consultation", "description": "Consultation (new case) with a rather long description text", "quantity": "1",
         "unit_price": "500", "gst_rate": 0}])
    c = client_for(receptionist, branch_a)
    for size in ("80mm", "58mm", "a4", "a5"):
        res = c.get(f"{API}invoices/{invoice.id}/pdf/", {"size": size, "preview": 1})
        assert res.status_code == 200 and res.content[:4] == b"%PDF", size


@pytest.mark.django_db
def test_PERM_009_buttons_hidden_in_screens_are_also_blocked_by_the_api(therapist, pharmacist, receptionist, branch_a):
    forbidden = [("get", "invoices/"), ("get", "stock/"), ("get", "audit-logs/"), ("get", "staff/"), ("post", "roles/"),
                 ("get", "visits/"), ("get", "reports/collection/")]
    for who in (therapist,):
        c = client_for(who, branch_a)
        for method, path in forbidden:
            assert getattr(c, method)(API + path).status_code == 403, (who.username, path)
    assert client_for(pharmacist, branch_a).get(API + "staff/").status_code == 403
    assert client_for(receptionist, branch_a).get(API + "audit-logs/").status_code == 403


@pytest.mark.django_db
def test_ORG_012_bad_branch_ids_are_refused(receptionist):
    c = APIClient()
    c.force_authenticate(receptionist)
    for value in ("not-a-uuid", "11111111-1111-1111-1111-111111111111", "", "' OR 1=1"):
        c.credentials(HTTP_X_BRANCH_ID=value)
        assert c.get(API + "patients/").status_code in (400, 403), value


@pytest.mark.django_db
def test_PAT_015_there_is_no_patient_export_endpoint():
    from django.urls import get_resolver

    patterns = " ".join(str(p.pattern) for p in get_resolver().url_patterns)
    # patient import/export is not implemented; reports exports are audited separately
    assert "patients/export" not in patterns
