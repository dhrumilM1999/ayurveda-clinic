"""
SMS adapter. The provider is chosen by SMS_PROVIDER in .env:
- "console": prints the SMS in the backend log (run logs.bat to see it) and saves it. Nothing is sent.
- "fast2sms": really sends the SMS through Fast2SMS (paid, about Rs 3-5 per SMS on the no-DLT route; add Rs 100 to the
  Fast2SMS wallet first). Needs FAST2SMS_API_KEY in .env.
- "fake": used by automated tests; keeps messages in memory.
Another paid gateway can be added later as one more class here.
"""
import json
import logging
import re
import urllib.parse
import urllib.request

from django.conf import settings

from apps.common.adapters import load_provider

from .models import OutboundMessage

logger = logging.getLogger("sms")

# Messages with these purposes contain secrets; they are not stored in the database.
SECRET_PURPOSES = {"login_otp"}


class BaseSmsProvider:
    name = "base"

    def send(self, to: str, message: str) -> str:
        """Send the message. Return a status like "sent" or "failed"."""
        raise NotImplementedError


class ConsoleSmsProvider(BaseSmsProvider):
    name = "console"

    def send(self, to, message):
        logger.warning("\n==== SMS (console, not really sent) ====\nTo: %s\n%s\n========================================", to, message)
        return "logged"


class FakeSmsProvider(BaseSmsProvider):
    name = "fake"
    outbox: list[dict] = []

    def send(self, to, message):
        FakeSmsProvider.outbox.append({"to": to, "message": message})
        return "sent"


class Fast2SmsProvider(BaseSmsProvider):
    """Sends a real SMS through https://www.fast2sms.com (API key in .env). Never raises: a failure is returned as "failed"."""

    name = "fast2sms"
    URL = "https://www.fast2sms.com/dev/bulkV2"

    def send(self, to, message):
        number = re.sub(r"\D", "", to or "")[-10:]
        key = getattr(settings, "FAST2SMS_API_KEY", "")
        if len(number) != 10 or not key:
            logger.error("Fast2SMS: no valid mobile number (%s) or no FAST2SMS_API_KEY", "ok" if len(number) == 10 else "missing")
            return "failed"
        body = urllib.parse.urlencode({
            "route": getattr(settings, "FAST2SMS_ROUTE", "q"), "message": message, "numbers": number, "flash": "0",
        }).encode()
        request = urllib.request.Request(self.URL, data=body, headers={"authorization": key, "Content-Type": "application/x-www-form-urlencoded"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310 - fixed https address
                answer = json.loads(response.read().decode("utf-8", "replace"))
        except Exception:  # noqa: BLE001 - a gateway problem must not crash the login screen
            logger.exception("Fast2SMS: the request failed")
            return "failed"
        if answer.get("return") is True:
            return "sent"
        logger.error("Fast2SMS refused the message: %s", answer.get("message"))
        return "failed"


PROVIDERS = {
    "fast2sms": "apps.notifications.sms.Fast2SmsProvider",
    "console": "apps.notifications.sms.ConsoleSmsProvider",
    "fake": "apps.notifications.sms.FakeSmsProvider",
}


def get_sms_provider() -> BaseSmsProvider:
    return load_provider("SMS", settings.SMS_PROVIDER, PROVIDERS)


def send_sms(to: str, message: str, organization=None, purpose: str = "") -> OutboundMessage:
    provider = get_sms_provider()
    status = provider.send(to, message)
    stored_body = "(hidden: contains a one-time password)" if purpose in SECRET_PURPOSES else message
    return OutboundMessage.objects.create(
        organization=organization, channel="sms", provider=provider.name,
        purpose=purpose, to=to, body=stored_body, status=status,
    )
