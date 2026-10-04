"""
SMS adapter. The provider is chosen by SMS_PROVIDER in .env:
- "console": prints the SMS in the backend log (run logs.bat to see it) and saves it. Nothing is sent.
- "fake": used by automated tests; keeps messages in memory.
A real paid SMS gateway can be added later as one more class here.
"""
import logging

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


PROVIDERS = {
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
