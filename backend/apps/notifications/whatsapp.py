"""
WhatsApp adapter. The provider is chosen by WHATSAPP_PROVIDER in .env:
- "click_to_chat" (free): we only build a link like https://wa.me/919812345678?text=...
  Staff click it, WhatsApp opens with the message already typed, and they press Send.
- "fake": used by automated tests.
The paid WhatsApp Business API can be added later as one more class here.
"""
from urllib.parse import quote

from django.conf import settings

from apps.common.adapters import load_provider

from .models import OutboundMessage


def whatsapp_number(phone: str) -> str:
    """Indian mobile in WhatsApp format: 98123 45678 -> 919812345678."""
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10:
        digits = "91" + digits
    return digits


class BaseWhatsAppProvider:
    name = "base"

    def prepare(self, to: str, message: str) -> tuple[str, str]:
        """Return (status, link). The link is empty when the provider sends by itself."""
        raise NotImplementedError


class ClickToChatProvider(BaseWhatsAppProvider):
    name = "click_to_chat"

    def prepare(self, to, message):
        return "link_ready", f"https://wa.me/{whatsapp_number(to)}?text={quote(message)}"


class FakeWhatsAppProvider(BaseWhatsAppProvider):
    name = "fake"
    outbox: list[dict] = []

    def prepare(self, to, message):
        FakeWhatsAppProvider.outbox.append({"to": to, "message": message})
        return "link_ready", f"https://wa.me/{whatsapp_number(to)}?text={quote(message)}"


PROVIDERS = {
    "click_to_chat": "apps.notifications.whatsapp.ClickToChatProvider",
    "fake": "apps.notifications.whatsapp.FakeWhatsAppProvider",
}


def get_whatsapp_provider() -> BaseWhatsAppProvider:
    return load_provider("WhatsApp", settings.WHATSAPP_PROVIDER, PROVIDERS)


def prepare_whatsapp(to: str, message: str, organization=None, purpose: str = "") -> str:
    """Record the message and return the link staff can click (empty if already sent)."""
    provider = get_whatsapp_provider()
    status, link = provider.prepare(to, message)
    OutboundMessage.objects.create(
        organization=organization, channel="whatsapp", provider=provider.name,
        purpose=purpose, to=to, body=message, status=status,
    )
    return link
