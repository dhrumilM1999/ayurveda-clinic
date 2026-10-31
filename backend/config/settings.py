"""
Django settings for the Ayurveda clinic software.

ASK FIRST before editing this file. Most things you may want to change
(passwords, providers, timeouts) live in the `.env` file in the project root instead.
"""
import os
from datetime import timedelta
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


# --- Small helpers to read settings from the environment (.env) -------------
def env(name, default=None):
    return os.environ.get(name, default)


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def env_int(name, default):
    value = os.environ.get(name)
    return int(value) if value not in (None, "") else default


def env_list(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# --- Core --------------------------------------------------------------------
# Debug mode shows detailed errors. It is OFF unless DJANGO_DEBUG=1 (only on your own PC).
# Anything that is not debug mode is treated as "production" = real patients, strictest rules.
DEBUG = env_bool("DJANGO_DEBUG", False) and env("APP_ENV", "development") != "production"
IS_PRODUCTION = not DEBUG
APP_ENV = "production" if IS_PRODUCTION else "development"
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me-before-using-real-data")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend")
# On a development PC the clinic's own network address (for example 192.168.1.50 when a phone opens the app) changes
# with the router, so any address is accepted while DEBUG is on. A live server (DEBUG off) uses only the list above.
if DEBUG:
    ALLOWED_HOSTS = ["*"]
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:8000" if DEBUG else "")
# 1 = the site is reached through an HTTPS proxy (Caddy): cookies become "secure" and HSTS is sent.
HTTPS = env_bool("DJANGO_HTTPS", False)
# Where the Django admin lives. Change it on the real server (e.g. ADMIN_URL=manage-7f3k2/).
ADMIN_URL = env("ADMIN_URL", "admin/").strip("/") + "/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    # Our modules (one app per module)
    "apps.common",
    "apps.organizations",
    "apps.accounts",
    "apps.audit",
    "apps.notifications",
    "apps.patients",
    "apps.appointments",
    "apps.emr",
    "apps.medicines",
    "apps.prescriptions",
    "apps.pharmacy",
    "apps.billing",
    "apps.reports",
    "apps.enquiries",
    "apps.therapy",
    "apps.documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.SecurityHeadersMiddleware",
    "apps.common.middleware.AdminLoginLimitMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# --- Database ----------------------------------------------------------------
# One database only: PostgreSQL, running in Docker (see docker-compose.yml).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "ayurveda"),
        "USER": env("POSTGRES_USER", "ayurveda"),
        "PASSWORD": env("POSTGRES_PASSWORD", ""),
        "HOST": env("POSTGRES_HOST", "db"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        # A cloud database (for example Supabase) needs POSTGRES_SSLMODE=require in .env. Empty = no SSL (local Docker).
        "OPTIONS": {"sslmode": env("POSTGRES_SSLMODE", "")} if env("POSTGRES_SSLMODE", "") else {},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# --- Passwords ---------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Language and time -------------------------------------------------------
LANGUAGE_CODE = "en"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

# --- Files -------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))

# Storage adapter: "local" keeps files in a folder (a Docker volume).
# Later "s3" can be added here without changing the rest of the app.
STORAGE_PROVIDER = env("STORAGE_PROVIDER", "local")
if STORAGE_PROVIDER != "local":
    raise ImproperlyConfigured(f"STORAGE_PROVIDER '{STORAGE_PROVIDER}' is not set up yet. Use 'local'.")
# "private" = patient photos and documents. Never served as public links; only through the
# API, after a permission check, and every download is written to the audit log.
PRIVATE_MEDIA_ROOT = Path(env("PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(PRIVATE_MEDIA_ROOT), "base_url": "/private-not-served/"},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Largest file staff may upload (megabytes)
MAX_UPLOAD_MB = env_int("MAX_UPLOAD_MB", 10)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# --- Email (Mailpit test inbox in development) -------------------------------
EMAIL_PROVIDER = env("EMAIL_PROVIDER", "mailpit")
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", "mailpit")
EMAIL_PORT = env_int("EMAIL_PORT", 1025)
# Real mailbox (free options: your own domain mail, Zoho, Gmail app password). Empty in development (Mailpit).
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = 15
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "clinic@example.com")

# --- API (Django REST Framework) ---------------------------------------------
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.common.exception_handler.friendly_exception_handler",
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "login_ip": env("THROTTLE_LOGIN_IP", "20/min"),
        "login_user": env("THROTTLE_LOGIN_USER", "5/min"),
        "otp": env("THROTTLE_OTP", "10/min"),
        "anon": "100/min",
        "verify": env("THROTTLE_VERIFY", "30/min"),
        "enquiry": env("THROTTLE_ENQUIRY", "10/hour"),
        "error_report": env("THROTTLE_ERROR_REPORT", "60/min"),
    },
}

# Address of the app that patients reach when they scan the QR code on a print-out (the "is this genuine?"
# page). On one PC this is http://localhost:5173; on the clinic network use the PC's address, later the website.
# AI helper (free, local): Ollama on this PC. Used by the "Translate" button next to Gujarati / Hindi names.
# AI_PROVIDER: ollama (real) | fake (tests) | off. If Ollama is not running the button says "AI is offline".
AI_PROVIDER = env("AI_PROVIDER", "ollama")
OLLAMA_URL = env("OLLAMA_URL", "http://host.docker.internal:11434").rstrip("/")
# A small model answers a short translation in a few seconds on a PC without a strong graphics card. A bigger one
# (for example gemma2:9b) is better at Gujarati but slow. "-1" = keep the model loaded in memory all day.
OLLAMA_MODEL = env("OLLAMA_MODEL", "qwen2.5:3b")
OLLAMA_KEEP_ALIVE = env("OLLAMA_KEEP_ALIVE", "-1")
AI_TIMEOUT_SECONDS = int(env("AI_TIMEOUT_SECONDS", "60"))

PUBLIC_APP_URL = env("PUBLIC_APP_URL", "http://localhost:5173").rstrip("/")

# Websites (comma separated, e.g. https://www.myclinic.in) that may send the online enquiry form from the browser.
# Empty = only the app's own /enquiry page (and an iframe of it) works. See docs/ONLINE_ENQUIRY.md.
ENQUIRY_ALLOWED_ORIGINS = [o.rstrip("/") for o in env_list("ENQUIRY_ALLOWED_ORIGINS", "")]

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=env_int("JWT_REFRESH_HOURS", 12)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Login limits are counted in the cache. In development one process is enough; on the real server several
# worker processes run, so the counters are kept in a shared folder (otherwise each worker counts alone).
if DEBUG:
    CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
else:
    CACHES = {"default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": env("CACHE_DIR", "/tmp/ayurveda_cache"),
    }}

# --- Login security ----------------------------------------------------------
OTP_LENGTH = 6
OTP_VALID_MINUTES = env_int("OTP_VALID_MINUTES", 5)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
# Development only: also show the OTP on the login screen so testing is easy.
# It can NEVER be on when debug mode is off, whatever .env says.
SHOW_DEV_OTP_ON_SCREEN = env_bool("SHOW_DEV_OTP_ON_SCREEN", False) and DEBUG
# How doctors/admins receive the login OTP: "sms" (SMS adapter) or "email" (to the e-mail saved on their account).
TWO_FACTOR_METHOD = env("TWO_FACTOR_METHOD", "sms").strip().lower()
# Login one-time password (OTP) for doctors and admins. OFF on the PC, where everyone logs in with username + password.
# ON by default on a live server. REQUIRE_2FA=0 switches it OFF (weaker security; only until SMS/e-mail works),
# REQUIRE_2FA=1 switches it on (needs a working SMS or e-mail provider).
REQUIRE_2FA = env_bool("REQUIRE_2FA", IS_PRODUCTION)
# Minutes without mouse/keyboard activity before the app logs the user out.
IDLE_TIMEOUT_MINUTES = env_int("IDLE_TIMEOUT_MINUTES", 15)
# The Vite dev server forwards the real browser IP in X-Forwarded-For.
# Behind the HTTPS proxy (Caddy) every request comes from the proxy, so the real address must be read from
# this header - otherwise all users would share one login limit and the audit log would show the proxy's IP.
# Only safe when the backend port is NOT reachable from the internet (only through the proxy).
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", DEBUG or HTTPS)

# Key that scrambles sensitive medical notes in the database. Keep it safe and never change it
# once real data exists (old notes would become unreadable). Empty = development key.
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", "")

# --- External service providers (see CLAUDE.md section 5) --------------------
SMS_PROVIDER = env("SMS_PROVIDER", "console")
# Only for SMS_PROVIDER=fast2sms. Route "q" = Quick SMS (no DLT paperwork).
FAST2SMS_API_KEY = env("FAST2SMS_API_KEY", "")
FAST2SMS_ROUTE = env("FAST2SMS_ROUTE", "q")
# WhatsApp: "click_to_chat" builds a wa.me link that staff click to send (free).
WHATSAPP_PROVIDER = env("WHATSAPP_PROVIDER", "click_to_chat")
# Low-stock alert: a medicine with this many packs or fewer is "low" (unless it has its own level), and the
# owner's WhatsApp number for the "send stock alert" button (free link, the person presses Send). Empty = no link.
STOCK_LOW_DEFAULT = int(env("STOCK_LOW_DEFAULT", "5"))
STOCK_ALERT_WHATSAPP = env("STOCK_ALERT_WHATSAPP", "")
# Payments: "static_upi" shows a UPI QR / link; staff mark the bill paid (free, no gateway).
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", "static_upi")

# --- Demo data ---------------------------------------------------------------
# reset-demo-data.bat only works when DEMO_MODE is true. Never true with real patients.
DEMO_MODE = env_bool("DEMO_MODE", False)

# --- Browser security headers ------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"  # the public /enquiry page is a screen of the React app: its framing is set by the web server
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
if HTTPS:
    # The proxy already redirects http -> https, so Django does not redirect (SECURE_SSL_REDIRECT stays off).
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env_int("HSTS_SECONDS", 31536000)  # browsers remember "https only" for 1 year
    # includeSubDomains also forces HTTPS on every other sub-site of vednathayurved.com. Switch it on only
    # when you are sure all of them have a working certificate.
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("HSTS_INCLUDE_SUBDOMAINS", False)
    SECURE_HSTS_PRELOAD = False
SECURE_SSL_REDIRECT = False

# --- Safety checks before the server may start with real data ----------------
from config.prod_rules import startup_problems  # noqa: E402

_problems = startup_problems(
    debug=DEBUG, secret_key=SECRET_KEY, field_encryption_key=FIELD_ENCRYPTION_KEY, sms_provider=SMS_PROVIDER,
    two_factor_method=TWO_FACTOR_METHOD, require_2fa=REQUIRE_2FA, allowed_hosts=ALLOWED_HOSTS,
)
if _problems and not env_bool("SKIP_STARTUP_CHECKS", False):
    raise ImproperlyConfigured(
        "The server will not start because it is not safe for real patient data:"
        + "\n - " + "\n - ".join(_problems)
    )

# Logs never contain passwords, tokens, OTPs or database values (see apps/common/logging_filters.py).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact": {"()": "apps.common.logging_filters.RedactFilter"}},
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple", "filters": ["redact"]}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

# Shown in the Error log so a developer knows which version the problem happened in. Set in .env (for example a date or git id).
APP_VERSION = env("APP_VERSION", "dev")

# Audit log: rows older than this many days are saved to AUDIT_ARCHIVE_DIR and removed (manage.py purge_audit_log).
# The database refuses anything shorter than 90 days. Keep the archive folder in your backups.
AUDIT_RETENTION_DAYS = max(90, env_int("AUDIT_RETENTION_DAYS", 90))
AUDIT_ARCHIVE_DIR = env("AUDIT_ARCHIVE_DIR", str(BASE_DIR / "audit_archive"))
