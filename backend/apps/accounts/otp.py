"""Create and check login OTPs (one-time passwords). The OTP goes out via the SMS adapter."""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.common.utils import mask_phone
from apps.notifications.sms import send_sms

from .models import LoginChallenge


def _hash(challenge_id, code: str) -> str:
    message = f"{challenge_id}:{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def start_challenge(user) -> tuple[LoginChallenge, str]:
    """Create a new OTP for the user and send it. Returns (challenge, code)."""
    if not can_deliver(user):
        raise OtpNotDeliverable
    code = "".join(str(secrets.randbelow(10)) for _ in range(settings.OTP_LENGTH))
    challenge = LoginChallenge(
        user=user, expires_at=timezone.now() + timedelta(minutes=settings.OTP_VALID_MINUTES),
    )
    challenge.code_hash = _hash(challenge.id, code)
    challenge.save()
    message = f"Your clinic login OTP is {code}. Valid for {settings.OTP_VALID_MINUTES} minutes."
    if settings.TWO_FACTOR_METHOD == "email":
        _send_by_email(user, message)
    else:
        send_sms(
            to=user.phone or "(no phone saved)", message=message,
            organization=user.organization, purpose="login_otp",
        )
    return challenge, code


class OtpNotDeliverable(Exception):
    """The OTP cannot be sent (for example the person has no e-mail address saved)."""


def can_deliver(user) -> bool:
    if settings.TWO_FACTOR_METHOD == "email":
        return bool((user.email or "").strip())
    return True


def _send_by_email(user, message):
    from django.core.mail import send_mail

    send_mail("Your clinic login OTP", message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)


def check_challenge(challenge: LoginChallenge, code: str) -> bool:
    """True if the code is right. Wrong tries are counted; the OTP stops working after too many."""
    if not challenge.is_usable():
        return False
    if hmac.compare_digest(challenge.code_hash, _hash(challenge.id, str(code).strip())):
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["used_at"])
        return True
    challenge.attempts += 1
    challenge.save(update_fields=["attempts"])
    return False


def phone_hint(user) -> str:
    """Where the OTP went, hidden in the middle: 98XXXXXX21 or ab****@gmail.com."""
    if settings.TWO_FACTOR_METHOD == "email" and user.email:
        name, _, domain = user.email.partition("@")
        return f"{name[:2]}{'*' * max(len(name) - 2, 2)}@{domain}"
    return mask_phone(user.phone)
