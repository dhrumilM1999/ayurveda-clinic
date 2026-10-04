"""
EncryptedTextField: text that is stored scrambled (encrypted) in the database.
Used for sensitive free-text medical notes. If someone copies the database file,
they cannot read these notes without the FIELD_ENCRYPTION_KEY from .env.

ASK FIRST before editing. Losing or changing FIELD_ENCRYPTION_KEY makes old notes unreadable.
Note: encrypted text cannot be searched.
"""
import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models

PREFIX = "enc:"


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        if settings.APP_ENV == "production":
            raise ImproperlyConfigured("Set FIELD_ENCRYPTION_KEY in .env before running in production.")
        # Development only: derive a key from the secret key.
        key = base64.urlsafe_b64encode(hashlib.sha256(f"{settings.SECRET_KEY}:fields".encode()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(text: str) -> str:
    return PREFIX + _fernet().encrypt(text.encode()).decode()


def decrypt(value: str) -> str:
    if not value or not value.startswith(PREFIX):
        return value  # plain text (e.g. written before encryption was added)
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken:
        return "[cannot be read: encryption key changed]"


class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        return decrypt(value) if value else value

    def to_python(self, value):
        return decrypt(value) if isinstance(value, str) else value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if not value:
            return value
        return value if value.startswith(PREFIX) else encrypt(value)
