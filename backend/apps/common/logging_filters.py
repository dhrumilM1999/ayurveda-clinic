"""
Keeps secrets and patient details out of the server log.
Anything that looks like a token, a password, an OTP or a database "Key (column)=(value)" is replaced by [hidden].
ASK FIRST before editing.
"""
import logging
import re

_PATTERNS = [
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.I), r"\1[hidden]"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]*"), "[hidden]"),  # JWT tokens
    (re.compile(r"(?i)((?:password|passwd|otp|token|secret|refresh|access)[\"']?\s*[:=]\s*[\"']?)[^\s\"',}&]+"), r"\1[hidden]"),
    (re.compile(r"(?i)(OTP is )\d{4,8}"), r"\1[hidden]"),
    (re.compile(r"Key \([^)]*\)=\([^)]*\)"), "Key [hidden]"),  # PostgreSQL: Key (phone)=(9812345621) already exists
]


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


class RedactFilter(logging.Filter):
    def filter(self, record):
        try:
            record.msg = redact(record.getMessage())
            record.args = None
        except Exception:  # never let logging break a request
            pass
        if record.exc_info:
            # Exception texts can hold values too: keep the type and a cleaned message, drop the rest of the detail.
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
        return True
