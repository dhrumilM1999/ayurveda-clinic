import re

import pytest

from apps.audit.models import AuditLog
from apps.notifications.models import OutboundMessage
from apps.notifications.sms import FakeSmsProvider
from conftest import PASSWORD

LOGIN = "/api/v1/auth/login/"
VERIFY = "/api/v1/auth/verify-otp/"
ME = "/api/v1/auth/me/"


def login(api, username, password=PASSWORD):
    return api.post(LOGIN, {"username": username, "password": password}, format="json")


def last_otp():
    return re.search(r"\b(\d{6})\b", FakeSmsProvider.outbox[-1]["message"]).group(1)


@pytest.mark.django_db
def test_receptionist_logs_in_without_otp(api, receptionist):
    response = login(api, "reception")
    assert response.status_code == 200
    assert response.data["otp_required"] is False
    assert response.data["access"] and response.data["refresh"]
    assert AuditLog.objects.filter(action="login", user=receptionist).exists()


@pytest.mark.django_db
def test_wrong_password_is_rejected_and_logged(api, receptionist):
    response = login(api, "reception", "not-the-password")
    assert response.status_code == 401
    assert "access" not in response.data
    assert AuditLog.objects.filter(action="login_failed", username="reception").exists()


@pytest.mark.django_db
def test_inactive_or_deleted_user_cannot_log_in(api, receptionist, org_admin):
    receptionist.delete(user=org_admin)
    assert login(api, "reception").status_code == 401


@pytest.mark.django_db
def test_doctor_needs_otp_then_gets_tokens(api, doctor):
    response = login(api, "doc")
    assert response.status_code == 200
    assert response.data["otp_required"] is True
    assert "access" not in response.data
    assert response.data["phone_hint"] == "98XXXXXX11"

    wrong = api.post(VERIFY, {"challenge_id": response.data["challenge_id"], "code": "000000"}, format="json")
    if last_otp() != "000000":
        assert wrong.status_code == 400

    ok = api.post(VERIFY, {"challenge_id": response.data["challenge_id"], "code": last_otp()}, format="json")
    assert ok.status_code == 200
    assert ok.data["access"]

    # An OTP works only once.
    again = api.post(VERIFY, {"challenge_id": response.data["challenge_id"], "code": last_otp()}, format="json")
    assert again.status_code == 400


@pytest.mark.django_db
def test_otp_is_not_stored_in_the_message_log(api, doctor):
    login(api, "doc")
    message = OutboundMessage.objects.get(purpose="login_otp")
    assert last_otp() not in message.body


@pytest.mark.django_db
def test_org_admin_needs_otp(api, org_admin):
    assert login(api, "owner").data["otp_required"] is True


@pytest.mark.django_db
def test_otp_locks_after_too_many_wrong_tries(api, doctor, settings):
    challenge_id = login(api, "doc").data["challenge_id"]
    real = last_otp()
    wrong = "111111" if real != "111111" else "222222"
    for _ in range(settings.OTP_MAX_ATTEMPTS):
        api.post(VERIFY, {"challenge_id": challenge_id, "code": wrong}, format="json")
    response = api.post(VERIFY, {"challenge_id": challenge_id, "code": real}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_login_is_rate_limited(api, receptionist):
    statuses = [login(api, "reception", "wrong-password").status_code for _ in range(6)]
    assert statuses[:5] == [401] * 5
    assert statuses[5] == 429  # "Too many requests"


@pytest.mark.django_db
def test_me_lists_only_my_branches_with_permissions(api, receptionist, branch_a, branch_b):
    token = login(api, "reception").data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    data = api.get(ME).data
    assert [b["code"] for b in data["branches"]] == ["A"]
    assert "patients.create" in data["branches"][0]["permissions"]
    assert "roles.manage" not in data["branches"][0]["permissions"]


@pytest.mark.django_db
def test_api_needs_login(api):
    assert api.get(ME).status_code == 401
    assert api.get("/api/v1/rooms/").status_code == 401
