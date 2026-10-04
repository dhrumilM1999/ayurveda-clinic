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
    code = "".join(str(secrets.randbelow(10)) for _ in range(settings.OTP_LENGTH))
    challenge = LoginChallenge(
        user=user, expires_at=timezone.now() + timedelta(minutes=settings.OTP_VALID_MINUTES),
    )
    challenge.code_hash = _hash(challenge.id, code)
    challenge.save()
    send_sms(
        to=user.phone or "(no phone saved)",
        message=f"Your clinic login OTP is {code}. Valid for {settings.OTP_VALID_MINUTES} minutes.",
        organization=user.organization,
        purpose="login_otp",
    )
    return challenge, code


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
    return mask_phone(user.phone)
