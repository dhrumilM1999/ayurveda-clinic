"""
Safety rules for running with REAL patient data ("production").
Used by settings.py (the app refuses to start when a rule is broken) and by the
`check_production_ready` command (prints PASS / FAIL for the owner).

ASK FIRST before editing this file.
"""

WEAK_SECRET_MARKERS = ("dev-only", "change-me", "changeme", "insecure", "secret", "password")
MIN_SECRET_LENGTH = 40


def secret_key_problem(key: str | None) -> str:
    """Return a plain-English problem with the secret key, or "" when it is fine."""
    key = (key or "").strip()
    if not key:
        return "DJANGO_SECRET_KEY is empty."
    lowered = key.lower()
    if any(marker in lowered for marker in WEAK_SECRET_MARKERS):
        return "DJANGO_SECRET_KEY still looks like the sample/development key."
    if len(key) < MIN_SECRET_LENGTH:
        return f"DJANGO_SECRET_KEY is too short (use at least {MIN_SECRET_LENGTH} random characters)."
    return ""


def startup_problems(*, debug, secret_key, field_encryption_key, sms_provider, two_factor_method,
                     require_2fa, allowed_hosts) -> list[str]:
    """Things that must be right before the server may start with debug switched off."""
    if debug:
        return []
    problems = []
    secret_problem = secret_key_problem(secret_key)
    if secret_problem:
        problems.append(secret_problem + " Make a long random one and put it in the server's settings file.")
    if not (field_encryption_key or "").strip():
        problems.append("FIELD_ENCRYPTION_KEY is empty. It scrambles medical notes in the database; "
                        "set it once and never change or lose it.")
    hosts = [h for h in allowed_hosts if h and h != "*"]
    if not hosts or "*" in allowed_hosts:
        problems.append("DJANGO_ALLOWED_HOSTS must list the real website name (not empty and not '*').")
    if require_2fa and two_factor_method == "sms" and sms_provider == "console":
        problems.append(
            "Doctors/admins need a one-time password (OTP) at login, but SMS_PROVIDER=console sends nothing. "
            "Choose ONE: (a) TWO_FACTOR_METHOD=email (OTP goes to the person's e-mail; needs real e-mail "
            "settings), (b) a real SMS gateway, or (c) REQUIRE_2FA=0 (turns the OTP step off - weaker; use "
            "only until e-mail or SMS is ready)."
        )
    return problems
