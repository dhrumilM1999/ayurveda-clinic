"""Small helper functions used by several modules."""
from django.conf import settings


def mask_phone(phone: str | None) -> str:
    """Hide the middle of a phone number for lists: 9812345621 -> 98XXXXXX21."""
    if not phone:
        return ""
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) <= 4:
        return "X" * len(digits)
    return digits[:2] + "X" * (len(digits) - 4) + digits[-2:]


def client_ip(request) -> str | None:
    """The IP address of the person making the request."""
    if request is None:
        return None
    if settings.TRUST_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
