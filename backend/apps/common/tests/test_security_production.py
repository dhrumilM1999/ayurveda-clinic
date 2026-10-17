"""
Proves the "live server" safety rules: strict settings, no OTP on screen, no secrets in logs,
safe headers, the admin page moved and limited, no demo commands, safe 2FA fallbacks.
"""
import logging
import os
from datetime import date
import subprocess
import sys
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.common.logging_filters import redact
from apps.notifications.sms import ConsoleSmsProvider
from conftest import PASSWORD, client_for, make_user
from config.prod_rules import secret_key_problem, startup_problems

BACKEND_DIR = Path(__file__).resolve().parents[3]
GOOD_KEY = "k9Zt3vQ8mXw2LpR7cYb5NfHd6JsAe1UgT4oVxKq0Wn8Bz5Dr2F"
FERNET_KEY = "Wn5Gw6bq0q2m7yY3X4p3dL1o8cVQz9rHk6tA2uJbE1s="


def load_settings(**env):
    """Start Python with a clean environment and read config.settings, like a real server start."""
    clean = {k: v for k, v in os.environ.items() if not k.startswith(("DJANGO_", "APP_", "SHOW_", "TWO_", "REQUIRE_", "FIELD_", "SMS_", "ADMIN_", "HSTS_", "SKIP_", "TRUST_"))}
    clean.update({"PYTHONPATH": str(BACKEND_DIR), **env})
    code = (
        "import json, config.settings as s;"
        "print(json.dumps({k: getattr(s, k, None) for k in ['DEBUG','IS_PRODUCTION','SHOW_DEV_OTP_ON_SCREEN','SESSION_COOKIE_SECURE',"
        "'CSRF_COOKIE_SECURE','SECURE_HSTS_SECONDS','SECURE_HSTS_INCLUDE_SUBDOMAINS','SECURE_SSL_REDIRECT','TRUST_X_FORWARDED_FOR',"
        "'ADMIN_URL','SECURE_PROXY_SSL_HEADER','CSRF_TRUSTED_ORIGINS']}, default=str))"
    )
    return subprocess.run([sys.executable, "-c", code], env=clean, cwd=BACKEND_DIR, capture_output=True, text=True)


PROD_ENV = {
    "DJANGO_SECRET_KEY": GOOD_KEY, "FIELD_ENCRYPTION_KEY": FERNET_KEY, "DJANGO_ALLOWED_HOSTS": "app.example.com",
    "SMS_PROVIDER": "console", "TWO_FACTOR_METHOD": "email",
}


# --- Settings rules --------------------------------------------------------------
def test_secret_key_rules():
    assert secret_key_problem("")
    assert secret_key_problem("dev-only-insecure-key-change-me-before-using-real-data")
    assert secret_key_problem("short")
    assert secret_key_problem("change-me-" + "a" * 60)
    assert secret_key_problem(GOOD_KEY) == ""


def test_server_refuses_to_start_with_the_sample_secret_key():
    result = load_settings(**{**PROD_ENV, "DJANGO_SECRET_KEY": "dev-only-insecure-key-change-me-before-using-real-data"})
    assert result.returncode != 0 and "not safe for real patient data" in result.stderr


def test_server_refuses_to_start_with_empty_secret_key_or_no_encryption_key():
    assert load_settings(**{**PROD_ENV, "DJANGO_SECRET_KEY": ""}).returncode != 0
    result = load_settings(**{**PROD_ENV, "FIELD_ENCRYPTION_KEY": ""})
    assert result.returncode != 0 and "FIELD_ENCRYPTION_KEY" in result.stderr


def test_a_made_up_encryption_key_is_refused():
    result = load_settings(**{**PROD_ENV, "FIELD_ENCRYPTION_KEY": "abc"})
    assert result.returncode != 0 and "not a valid key" in result.stderr


def test_debug_is_off_by_default_and_hosts_must_be_real():
    assert load_settings(**{**PROD_ENV, "DJANGO_ALLOWED_HOSTS": "*"}).returncode != 0
    import json

    ok = load_settings(**PROD_ENV)
    assert ok.returncode == 0, ok.stderr
    assert json.loads(ok.stdout)["DEBUG"] is False


def test_console_sms_without_a_two_step_fallback_is_refused():
    env = {**PROD_ENV, "TWO_FACTOR_METHOD": "sms"}
    result = load_settings(**env)
    assert result.returncode != 0 and "OTP" in result.stderr
    # ...the two safe ways out:
    assert load_settings(**{**env, "REQUIRE_2FA": "0"}).returncode == 0
    assert load_settings(**{**env, "TWO_FACTOR_METHOD": "email"}).returncode == 0


def test_otp_can_never_be_shown_on_screen_when_debug_is_off():
    import json

    result = load_settings(**{**PROD_ENV, "SHOW_DEV_OTP_ON_SCREEN": "true", "DJANGO_DEBUG": "0"})
    assert json.loads(result.stdout)["SHOW_DEV_OTP_ON_SCREEN"] is False
    # even APP_ENV=production with DJANGO_DEBUG=1 cannot switch debug on
    result = load_settings(**{**PROD_ENV, "SHOW_DEV_OTP_ON_SCREEN": "true", "DJANGO_DEBUG": "1", "APP_ENV": "production"})
    data = json.loads(result.stdout)
    assert data["DEBUG"] is False and data["SHOW_DEV_OTP_ON_SCREEN"] is False


def test_https_switch_turns_on_secure_cookies_and_hsts():
    import json

    data = json.loads(load_settings(**{**PROD_ENV, "DJANGO_HTTPS": "1"}).stdout)
    assert data["SESSION_COOKIE_SECURE"] and data["CSRF_COOKIE_SECURE"]
    assert data["SECURE_HSTS_SECONDS"] == 31536000
    assert data["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is False  # careful default, see settings.py
    assert data["SECURE_SSL_REDIRECT"] is False  # the proxy redirects
    assert data["SECURE_PROXY_SSL_HEADER"]
    assert data["TRUST_X_FORWARDED_FOR"] is True
    off = json.loads(load_settings(**PROD_ENV).stdout)
    assert not off["SESSION_COOKIE_SECURE"] and not off["SECURE_HSTS_SECONDS"]


def test_admin_address_comes_from_env():
    import json

    assert json.loads(load_settings(**{**PROD_ENV, "ADMIN_URL": "/manage-x9/"}).stdout)["ADMIN_URL"] == "manage-x9/"


def test_startup_problems_is_quiet_in_debug():
    assert startup_problems(debug=True, secret_key="", field_encryption_key="", sms_provider="console",
                            two_factor_method="sms", require_2fa=True, allowed_hosts=[]) == []


# --- Headers, CORS, admin ---------------------------------------------------------
@pytest.mark.django_db
def test_api_answers_carry_safe_headers_and_are_never_cached(org, roles, branch_a):
    user = make_user(org, "rec", {branch_a: roles["receptionist"]})
    client = client_for(user, branch_a)
    response = client.get("/api/v1/patients/")
    assert response["Cache-Control"].startswith("no-store")
    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "same-origin"
    assert "camera=()" in response["Permissions-Policy"]


@pytest.mark.django_db
def test_other_websites_get_no_cors_permission_on_private_addresses():
    response = APIClient().post("/api/v1/auth/login/", {"username": "a", "password": "b"}, format="json",
                                HTTP_ORIGIN="https://evil.example")
    assert "Access-Control-Allow-Origin" not in response
    option = APIClient().options("/api/v1/patients/", HTTP_ORIGIN="https://evil.example",
                                 HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET")
    assert "Access-Control-Allow-Origin" not in option


@pytest.mark.django_db
def test_browsable_api_is_off_and_errors_show_no_internals(org, roles, branch_a):
    client = client_for(make_user(org, "rec", {branch_a: roles["receptionist"]}), branch_a)
    response = client.get("/api/v1/patients/", HTTP_ACCEPT="text/html")
    assert response["Content-Type"].startswith("application/json")
    bad = client.get("/api/v1/patients/not-a-real-id/")
    text = bad.content.decode()
    for word in ("Traceback", "SELECT ", "django.db", "File \""):
        assert word not in text


@pytest.mark.django_db
def test_admin_moves_to_the_configured_address_and_login_is_limited(settings, client):
    from django.urls import clear_url_caches

    settings.ADMIN_URL = "manage-x9/"
    import importlib

    import config.urls

    clear_url_caches()
    importlib.reload(config.urls)
    try:
        assert client.get("/manage-x9/login/").status_code == 200
        assert client.get("/admin/login/").status_code == 404
        statuses = [client.post("/manage-x9/login/", {"username": "x", "password": "y"}).status_code for _ in range(14)]
        assert 429 in statuses and statuses[0] != 429
    finally:
        settings.ADMIN_URL = "admin/"
        clear_url_caches()
        importlib.reload(config.urls)


# --- Logs ------------------------------------------------------------------------
def test_console_sms_in_production_hides_number_and_code(settings, caplog):
    settings.IS_PRODUCTION = True
    with caplog.at_level(logging.WARNING, logger="sms"):
        ConsoleSmsProvider().send("9812345621", "Your clinic login OTP is 482913. Valid for 5 minutes.")
    text = caplog.text
    assert "482913" not in text and "9812345621" not in text and "98XXXXXX21" in text


def test_console_sms_in_development_still_shows_the_code(settings, caplog):
    settings.IS_PRODUCTION = False
    with caplog.at_level(logging.WARNING, logger="sms"):
        ConsoleSmsProvider().send("9812345621", "Your clinic login OTP is 482913.")
    assert "482913" in caplog.text


def test_log_filter_hides_tokens_passwords_and_database_values():
    assert "abc123" not in redact("Authorization: Bearer abc123.def456")
    assert "Secret9" not in redact('{"password": "Secret9", "x": 1}')
    assert "9812345621" not in redact("DETAIL:  Key (mobile)=(9812345621) already exists.")
    assert "482913" not in redact("Your clinic login OTP is 482913.")
    assert redact("Patient list loaded") == "Patient list loaded"
    token = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoiMSJ9.sig_nature_value"
    assert token not in redact(f"refresh was {token}")


@pytest.mark.django_db
def test_audit_log_has_no_edit_or_delete_address_and_cannot_be_changed(org, roles, branch_a, org_admin):
    client = client_for(org_admin, branch_a)
    client.get("/api/v1/patients/")  # make sure there is something in the log
    entry = AuditLog.objects.create(organization=org, username="x", action="view")
    for method in ("put", "patch", "delete", "post"):
        assert getattr(client, method)(f"/api/v1/audit-logs/{entry.id}/", {}, format="json").status_code == 405
    assert client.post("/api/v1/audit-logs/", {}, format="json").status_code == 405
    with pytest.raises(PermissionError):
        entry.delete()
    with pytest.raises(PermissionError):
        AuditLog.objects.filter(id=entry.id).update(action="login")


@pytest.mark.django_db
def test_login_failure_log_and_audit_never_store_the_password(api, org_admin):
    api.post("/api/v1/auth/login/", {"username": "owner", "password": "My-Secret-Pw-77"}, format="json")
    for entry in AuditLog.objects.all():
        assert "My-Secret-Pw-77" not in str(entry.changes) + entry.object_repr + entry.username


# --- Demo leftovers ---------------------------------------------------------------
@pytest.mark.django_db
def test_demo_commands_refuse_to_run_on_the_live_server(settings):
    settings.IS_PRODUCTION = True
    settings.DEMO_MODE = False
    for name in ("seed_demo", "seed_demo_journey", "use_single_doctor"):
        with pytest.raises(CommandError, match="Refusing"):
            call_command(name)
    assert not User.objects.exists()


@pytest.mark.django_db
def test_check_production_ready_fails_on_a_demo_setup_and_passes_the_basics(settings, tmp_path, monkeypatch):
    call_command("seed_demo", verbosity=0)
    from apps.common.management.commands.check_production_ready import run_checks

    def levels():
        return {title: level for level, title, _ in run_checks()}

    result = levels()
    assert result["No demo users exist"] == "FAIL"
    assert result["No demo patients exist"] == "FAIL"
    assert result["Django admin address was changed"] == "FAIL"
    with pytest.raises(CommandError, match="NOT READY"):
        call_command("check_production_ready")

    # A clean live setup
    settings.DEBUG = False
    settings.SECRET_KEY = GOOD_KEY
    settings.FIELD_ENCRYPTION_KEY = FERNET_KEY
    settings.ALLOWED_HOSTS = ["app.example.com"]
    settings.CSRF_TRUSTED_ORIGINS = ["https://app.example.com"]
    settings.PUBLIC_APP_URL = "https://app.example.com"
    settings.HTTPS = True
    settings.SESSION_COOKIE_SECURE = settings.CSRF_COOKIE_SECURE = True
    settings.SECURE_HSTS_SECONDS = 100
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    settings.TRUST_X_FORWARDED_FOR = True
    settings.ADMIN_URL = "manage-x9/"
    settings.DEMO_MODE = False
    settings.REQUIRE_2FA = True
    settings.TWO_FACTOR_METHOD = "email"
    settings.EMAIL_PROVIDER, settings.EMAIL_HOST = "smtp", "smtp.example.com"
    monkeypatch.setenv("POSTGRES_PASSWORD", "a-long-random-database-password")
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    monkeypatch.delenv("SHOW_DEV_OTP_ON_SCREEN", raising=False)
    monkeypatch.delenv("SKIP_STARTUP_CHECKS", raising=False)
    (tmp_path / "db.dump").write_text("x")
    result = levels()
    for title in ("Debug mode is off", "Secret key is strong", "Medical-notes encryption key is set",
                  "Allowed website names are the real ones", "Trusted origins are https and not localhost",
                  "Django admin address was changed", "DEMO_MODE is off", "Login code is NOT shown on the screen",
                  "Database password is not a sample one", "Login codes are delivered by email"):
        assert result[title] == "PASS", title
    assert result["HTTPS settings are on (secure cookies, HSTS, proxy header)"] == "PASS"
    assert result["No demo users exist"] == "FAIL"  # still there until the owner removes them


@pytest.mark.django_db
def test_no_demo_users_or_patients_appear_on_their_own(org, roles):
    """ensure_defaults (runs on every start) adds dropdowns and consent text only - no people."""
    call_command("ensure_defaults", verbosity=0)
    from apps.patients.models import Patient

    assert not Patient.objects.exists() and not User.objects.exists()


# --- Two-step login fallbacks -----------------------------------------------------
@pytest.mark.django_db
def test_otp_by_email_goes_to_the_mailbox_not_the_sms_log(api, doctor, settings, mailoutbox):
    settings.TWO_FACTOR_METHOD = "email"
    doctor.email = "dr.sample@example.com"
    doctor.save()
    response = api.post("/api/v1/auth/login/", {"username": "doc", "password": PASSWORD}, format="json")
    assert response.status_code == 200 and response.data["otp_required"] is True
    assert "dev_otp" not in response.data
    assert response.data["phone_hint"].startswith("dr") and "@example.com" in response.data["phone_hint"]
    assert len(mailoutbox) == 1 and mailoutbox[0].to == ["dr.sample@example.com"]
    code = [w for w in mailoutbox[0].body.split() if w.strip(".").isdigit() and len(w.strip(".")) == 6][0].strip(".")
    verify = api.post("/api/v1/auth/verify-otp/", {"challenge_id": response.data["challenge_id"], "code": code}, format="json")
    assert verify.status_code == 200 and verify.data["access"]


@pytest.mark.django_db
def test_otp_by_email_without_an_email_address_gives_a_clear_message(api, doctor, settings):
    settings.TWO_FACTOR_METHOD = "email"
    doctor.email = ""
    doctor.save()
    response = api.post("/api/v1/auth/login/", {"username": "doc", "password": PASSWORD}, format="json")
    assert response.status_code == 400 and "e-mail" in response.data["detail"]
    assert "access" not in response.data


@pytest.mark.django_db
def test_switching_two_step_login_off_lets_doctors_in_directly(api, doctor, settings):
    settings.REQUIRE_2FA = False
    response = api.post("/api/v1/auth/login/", {"username": "doc", "password": PASSWORD}, format="json")
    assert response.data["otp_required"] is False and response.data["access"]


@pytest.mark.django_db
def test_no_dev_otp_in_the_login_answer_when_debug_is_off(api, doctor, settings):
    settings.SHOW_DEV_OTP_ON_SCREEN = False
    response = api.post("/api/v1/auth/login/", {"username": "doc", "password": PASSWORD}, format="json")
    assert "dev_otp" not in response.data
    assert "dev_otp" not in str(response.content)


# --- Sessions ---------------------------------------------------------------------
@pytest.mark.django_db
def test_logout_and_password_reset_end_the_old_refresh_tokens(api, org_admin, receptionist, branch_a):
    login = api.post("/api/v1/auth/login/", {"username": "reception", "password": PASSWORD}, format="json").data
    refresh = login["refresh"]
    # a manager resets the password: the old session's refresh token stops working
    admin_client = client_for(org_admin, branch_a)
    reset = admin_client.post(f"/api/v1/staff/{receptionist.id}/set-password/", {"password": "Brand-New-Pass-2026!"}, format="json")
    assert reset.status_code == 204
    assert api.post("/api/v1/auth/refresh/", {"refresh": refresh}, format="json").status_code == 401
    # logout blacklists the token
    login2 = api.post("/api/v1/auth/login/", {"username": "reception", "password": "Brand-New-Pass-2026!"}, format="json").data
    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION=f"Bearer {login2['access']}")
    assert authed.post("/api/v1/auth/logout/", {"refresh": login2["refresh"]}, format="json").status_code == 204
    assert api.post("/api/v1/auth/refresh/", {"refresh": login2["refresh"]}, format="json").status_code == 401


@pytest.mark.django_db
def test_a_switched_off_account_cannot_refresh_or_use_its_token(api, org_admin, receptionist):
    login = api.post("/api/v1/auth/login/", {"username": "reception", "password": PASSWORD}, format="json").data
    receptionist.is_active = False
    receptionist.save()
    assert api.post("/api/v1/auth/refresh/", {"refresh": login["refresh"]}, format="json").status_code == 401
    authed = APIClient()
    authed.credentials(HTTP_AUTHORIZATION=f"Bearer {login['access']}")
    assert authed.get("/api/v1/auth/me/").status_code == 401


@pytest.mark.django_db
def test_login_does_not_reveal_which_usernames_exist(api, receptionist):
    unknown = api.post("/api/v1/auth/login/", {"username": "nobody-here", "password": "whatever-123"}, format="json")
    wrong = api.post("/api/v1/auth/login/", {"username": "reception", "password": "whatever-123"}, format="json")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.data == wrong.data


@pytest.mark.django_db
def test_weak_passwords_are_refused(api, org_admin, branch_a):
    client = client_for(org_admin, branch_a)
    for weak in ("short1!", "password123456", "1234567890123"):
        response = client.post("/api/v1/auth/change-password/", {"old_password": PASSWORD, "new_password": weak}, format="json")
        assert response.status_code == 400, weak


@pytest.mark.django_db
def test_verify_page_shows_only_initials(org, branch_a, org_admin):
    from apps.documents.models import IssuedDocument
    from apps.patients.models import Patient

    patient = Patient.objects.create(organization=org, first_name="Ramesh", last_name="Patel", mobile="9811000001",
                                     gender="male")
    doc = IssuedDocument.objects.create(organization=org, branch=branch_a, patient=patient, kind="prescription",
                                        number="RX/1", object_id="1", issued_on=date.today())
    body = APIClient().get(f"/api/v1/verify/{doc.token}/").content.decode()
    assert "R. P." in body
    for secret in ("Ramesh", "Patel", "9811000001"):
        assert secret not in body


def test_pdf_maker_refuses_files_and_websites_but_allows_embedded_pictures(tmp_path):
    from weasyprint import HTML

    from apps.common.pdf_safety import check_address, embedded_only_fetcher

    secret = tmp_path / "secret.png"
    secret.write_bytes(b"not an image")
    with pytest.raises(ValueError):
        check_address(secret.as_uri())
    with pytest.raises(ValueError):
        check_address("http://169.254.169.254/latest/meta-data/")
    pixel = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    pdf = HTML(string=f'<img src="{pixel}"><img src="{secret.as_uri()}">', url_fetcher=embedded_only_fetcher).write_pdf()
    assert pdf.startswith(b"%PDF")
