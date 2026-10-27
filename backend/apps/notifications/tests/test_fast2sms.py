import io
import json
import urllib.parse

import pytest

from apps.notifications import sms


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_fast2sms_sends_the_otp_to_a_10_digit_number(settings, monkeypatch):
    settings.FAST2SMS_API_KEY = "test-key"
    seen = {}

    def fake_open(request, timeout):
        seen["data"] = urllib.parse.parse_qs(request.data.decode())
        seen["key"] = request.get_header("Authorization")
        return FakeResponse(json.dumps({"return": True, "request_id": "x", "message": ["SMS sent successfully."]}).encode())

    monkeypatch.setattr(sms.urllib.request, "urlopen", fake_open)
    assert sms.Fast2SmsProvider().send("+91 97256-19634", "Your clinic login OTP is 123456.") == "sent"
    assert seen["data"]["numbers"] == ["9725619634"] and seen["key"] == "test-key" and seen["data"]["route"] == ["q"]


def test_a_refused_or_broken_gateway_is_reported_not_raised(settings, monkeypatch):
    settings.FAST2SMS_API_KEY = "test-key"
    monkeypatch.setattr(sms.urllib.request, "urlopen", lambda r, timeout: FakeResponse(json.dumps({"return": False, "message": "Low balance"}).encode()))
    assert sms.Fast2SmsProvider().send("9725619634", "x") == "failed"

    def boom(r, timeout):
        raise OSError("no internet")
    monkeypatch.setattr(sms.urllib.request, "urlopen", boom)
    assert sms.Fast2SmsProvider().send("9725619634", "x") == "failed"


def test_no_key_or_no_number_sends_nothing(settings, monkeypatch):
    monkeypatch.setattr(sms.urllib.request, "urlopen", lambda *a, **k: pytest.fail("must not call the gateway"))
    settings.FAST2SMS_API_KEY = ""
    assert sms.Fast2SmsProvider().send("9725619634", "x") == "failed"
    settings.FAST2SMS_API_KEY = "k"
    assert sms.Fast2SmsProvider().send("(no phone saved)", "x") == "failed"
