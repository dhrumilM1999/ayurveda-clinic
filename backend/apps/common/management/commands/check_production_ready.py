"""
Run this on the LIVE server to see whether it is safe for real patients:

    docker compose exec backend python manage.py check_production_ready

It prints PASS / WARN / FAIL for each check. Any FAIL makes the command end with an error code (exit 1).
WARN = please read it and decide. It changes nothing.
"""
import os
import time
from pathlib import Path

from django.conf import settings
from django.core import checks
from django.core.management.base import BaseCommand, CommandError

from config.prod_rules import secret_key_problem

DEMO_PASSWORD = "Ayur@2026"
DEMO_USERNAMES = ["admin", "doctor1", "reception1", "therapist1", "pharmacist1"]
DEMO_PHONE_PREFIXES = ("981100", "999990")  # the made-up numbers used by seed_demo and seed_demo_journey
WEAK_DB_PASSWORDS = {"", "ayurveda_dev_password", "ayurveda", "postgres", "password"}


def _env_true(name):
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def run_checks():
    """Return a list of (level, title, advice); level is PASS, WARN or FAIL."""
    results = []

    def add(level, title, advice=""):
        results.append((level, title, advice))

    # --- Core ---
    add("FAIL" if settings.DEBUG else "PASS", "Debug mode is off",
        "Set DJANGO_DEBUG=0 (debug mode shows internal details to visitors).")
    problem = secret_key_problem(settings.SECRET_KEY)
    add("FAIL" if problem else "PASS", "Secret key is strong", problem)
    add("PASS" if settings.FIELD_ENCRYPTION_KEY else "FAIL", "Medical-notes encryption key is set",
        "Set FIELD_ENCRYPTION_KEY once and keep a safe copy; losing it makes old notes unreadable.")
    hosts = [h for h in settings.ALLOWED_HOSTS if h]
    bad_hosts = not hosts or "*" in hosts or all(h in ("localhost", "127.0.0.1", "backend") for h in hosts)
    add("FAIL" if bad_hosts else "PASS", "Allowed website names are the real ones",
        "Set DJANGO_ALLOWED_HOSTS to the real app address (not empty, not '*', not only localhost).")
    csrf = settings.CSRF_TRUSTED_ORIGINS
    csrf_bad = (not csrf) or any(not o.startswith("https://") or "localhost" in o for o in csrf)
    add("FAIL" if csrf_bad else "PASS", "Trusted origins are https and not localhost",
        "Set DJANGO_CSRF_TRUSTED_ORIGINS=https://your-app-address")
    app_url = settings.PUBLIC_APP_URL
    add("FAIL" if (not app_url.startswith("https://") or "localhost" in app_url) else "PASS",
        "PUBLIC_APP_URL (QR codes and WhatsApp links) is the real https address", "Set PUBLIC_APP_URL=https://...")

    # --- HTTPS ---
    https_ok = bool(settings.HTTPS and settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE
                    and settings.SECURE_HSTS_SECONDS > 0 and settings.SECURE_PROXY_SSL_HEADER)
    add("PASS" if https_ok else "FAIL", "HTTPS settings are on (secure cookies, HSTS, proxy header)",
        "Set DJANGO_HTTPS=1 (the site must be reached only through the HTTPS proxy).")
    if settings.HTTPS and not settings.SECURE_HSTS_INCLUDE_SUBDOMAINS:
        add("WARN", "HSTS does not include sub-domains",
            "This is the careful default. Set HSTS_INCLUDE_SUBDOMAINS=1 only if every sub-site has a working certificate.")
    add("PASS" if settings.TRUST_X_FORWARDED_FOR else "WARN", "Real visitor address is read from the proxy",
        "Without it the login limit and the audit log see only the proxy's address (TRUST_X_FORWARDED_FOR=1).")

    # --- Admin site ---
    add("FAIL" if settings.ADMIN_URL == "admin/" else "PASS", "Django admin address was changed",
        "Set ADMIN_URL=something-hard-to-guess/ so bots cannot find the admin login.")

    # --- Login security ---
    if settings.SHOW_DEV_OTP_ON_SCREEN:
        add("FAIL", "Login code is NOT shown on the screen", "Remove SHOW_DEV_OTP_ON_SCREEN from the settings file.")
    elif _env_true("SHOW_DEV_OTP_ON_SCREEN"):
        add("WARN", "Login code is NOT shown on the screen",
            "SHOW_DEV_OTP_ON_SCREEN is set in the settings file. It has no effect while debug is off, but remove it to be safe.")
    else:
        add("PASS", "Login code is NOT shown on the screen")
    if not settings.REQUIRE_2FA:
        add("WARN", "Two-step login (OTP) for doctors and admins is SWITCHED OFF",
            "Weaker security. Use strong passwords and turn it on (REQUIRE_2FA=1) as soon as e-mail or SMS delivery works.")
    elif settings.TWO_FACTOR_METHOD == "sms" and settings.SMS_PROVIDER == "console":
        add("FAIL", "Login codes can actually be delivered",
            "SMS_PROVIDER=console sends nothing. Use TWO_FACTOR_METHOD=email.")
    elif settings.TWO_FACTOR_METHOD == "email" and (settings.EMAIL_PROVIDER == "mailpit"
                                                   or settings.EMAIL_HOST in ("mailpit", "localhost")):
        add("FAIL", "Login codes can actually be delivered",
            "TWO_FACTOR_METHOD=email but the e-mail settings still point to the test inbox. Set EMAIL_HOST/USER/PASSWORD.")
    else:
        add("PASS", f"Login codes are delivered by {settings.TWO_FACTOR_METHOD}")
    add("WARN" if settings.SMS_PROVIDER == "console" else "PASS", f"SMS provider is '{settings.SMS_PROVIDER}'",
        "'console' sends no real SMS (appointment reminders etc. will not reach patients).")

    # --- Demo leftovers ---
    from apps.accounts.models import User
    from apps.patients.models import Patient

    demo_users = list(User.objects.filter(username__in=DEMO_USERNAMES))
    weak = [u.username for u in demo_users if u.check_password(DEMO_PASSWORD)]
    detail = "Found: " + ", ".join(u.username for u in demo_users)
    if weak:
        detail += f" (password is still the well-known sample one for: {', '.join(weak)})"
    add("FAIL" if demo_users else "PASS", "No demo users exist",
        detail + ". Create your own accounts, then switch these off in Staff.")
    demo_patients = sum(
        Patient.objects.filter(is_deleted=False, mobile__startswith=prefix).count() for prefix in DEMO_PHONE_PREFIXES
    )
    add("FAIL" if demo_patients else "PASS", "No demo patients exist",
        f"{demo_patients} made-up patients found (mobile 981100xxxx / 999990xxxx).")
    add("FAIL" if settings.DEMO_MODE else "PASS", "DEMO_MODE is off", "Set DEMO_MODE=0 (it allows wiping all data).")

    # --- Database and backups ---
    add("FAIL" if os.environ.get("POSTGRES_PASSWORD", "") in WEAK_DB_PASSWORDS else "PASS",
        "Database password is not a sample one", "Set a long random POSTGRES_PASSWORD.")
    backup_dir = os.environ.get("BACKUP_DIR", "")
    if not backup_dir:
        add("FAIL", "Backups folder is configured", "Set BACKUP_DIR to the folder where daily database backups are saved.")
    elif not Path(backup_dir).is_dir():
        add("WARN", "Backups folder is visible", f"{backup_dir} cannot be seen from here; check it on the server.")
    else:
        newest = max((f.stat().st_mtime for f in Path(backup_dir).iterdir() if f.is_file()), default=0)
        age_h = (time.time() - newest) / 3600 if newest else None
        if age_h is None or age_h > 48:
            add("FAIL", "A backup was made in the last 2 days", "No recent backup file in " + backup_dir)
        else:
            add("PASS", f"A backup was made {age_h:.0f} hour(s) ago")

    # --- Leftover bypass ---
    add("FAIL" if _env_true("SKIP_STARTUP_CHECKS") else "PASS", "Start-up safety checks are not bypassed",
        "Remove SKIP_STARTUP_CHECKS from the settings file.")

    # --- Django's own deployment checks (anything not already covered above) ---
    for message in checks.run_checks(include_deployment_checks=True):
        if message.level >= checks.WARNING and message.id not in ("security.W004", "security.W008", "security.W021"):
            add("WARN", f"Django check {message.id}", message.msg)
    return results


class Command(BaseCommand):
    help = "Print PASS / WARN / FAIL for everything that must be right before real patients use the system."

    def handle(self, *args, **options):
        results = run_checks()
        colour = {"PASS": self.style.SUCCESS, "WARN": self.style.WARNING, "FAIL": self.style.ERROR}
        for level, title, advice in results:
            self.stdout.write(colour[level](f"[{level}] ") + title)
            if level != "PASS" and advice:
                self.stdout.write(f"        -> {advice}")
        fails = sum(1 for r in results if r[0] == "FAIL")
        warns = sum(1 for r in results if r[0] == "WARN")
        self.stdout.write("")
        if fails:
            raise CommandError(f"NOT READY: {fails} problem(s) to fix, {warns} warning(s).")
        self.stdout.write(self.style.SUCCESS(f"READY: all checks passed ({warns} warning(s) to read)."))
