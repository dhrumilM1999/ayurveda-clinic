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
APP_ENV = env("APP_ENV", "development")  # "development" or "production"
DEBUG = env_bool("DJANGO_DEBUG", APP_ENV == "development")
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me-before-using-real-data")
if APP_ENV == "production" and SECRET_KEY.startswith("dev-only"):
    raise ImproperlyConfigured("Set a real DJANGO_SECRET_KEY in .env before running in production.")

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://localhost:8000")

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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "clinic@example.com")

# --- API (Django REST Framework) ---------------------------------------------
REST_FRAMEWORK = {
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
    },
}

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

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# --- Login security ----------------------------------------------------------
OTP_LENGTH = 6
OTP_VALID_MINUTES = env_int("OTP_VALID_MINUTES", 5)
OTP_MAX_ATTEMPTS = env_int("OTP_MAX_ATTEMPTS", 5)
# Development only: also show the OTP on the login screen so testing is easy.
SHOW_DEV_OTP_ON_SCREEN = env_bool("SHOW_DEV_OTP_ON_SCREEN", False) and DEBUG
# Minutes without mouse/keyboard activity before the app logs the user out.
IDLE_TIMEOUT_MINUTES = env_int("IDLE_TIMEOUT_MINUTES", 15)
# The Vite dev server forwards the real browser IP in X-Forwarded-For.
TRUST_X_FORWARDED_FOR = env_bool("TRUST_X_FORWARDED_FOR", DEBUG)

# Key that scrambles sensitive medical notes in the database. Keep it safe and never change it
# once real data exists (old notes would become unreadable). Empty = development key.
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", "")

# --- External service providers (see CLAUDE.md section 5) --------------------
SMS_PROVIDER = env("SMS_PROVIDER", "console")
# WhatsApp: "click_to_chat" builds a wa.me link that staff click to send (free).
WHATSAPP_PROVIDER = env("WHATSAPP_PROVIDER", "click_to_chat")

# --- Demo data ---------------------------------------------------------------
# reset-demo-data.bat only works when DEMO_MODE is true. Never true with real patients.
DEMO_MODE = env_bool("DEMO_MODE", False)

# --- Browser security headers ------------------------------------------------
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SECURE_REFERRER_POLICY = "same-origin"
if APP_ENV == "production":
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "[{levelname}] {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}
