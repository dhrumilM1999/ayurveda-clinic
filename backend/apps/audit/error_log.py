"""
record_error(): the one function that writes a line in the Error log.
It is used by the server's error handler (apps/common/exception_handler.py) and by the screen's error report
(POST /error-logs/report/). It never raises: a problem while writing the log must not make things worse.

What is NOT stored: typed text, request bodies, the part of a web address after "?". Only what went wrong,
where, and to whom.
"""
import hashlib
import logging
import re
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.common.utils import client_ip

from .models import ErrorLog

logger = logging.getLogger(__name__)

SAME_PROBLEM_WINDOW = timedelta(hours=6)  # the same problem again inside this time is counted on one line
MAX_MESSAGE = 1000
MAX_DETAILS = 20000
MAX_TRAIL = 40

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
_NUMBER = re.compile(r"(?<=/)\d+(?=/|$)")
_SESSION = re.compile(r"[^A-Za-z0-9_-]")


def normalize_path(path: str) -> str:
    """/api/v1/patients/3f2a.../ -> /api/v1/patients/:id/  (so the same problem on different records is one problem)."""
    path = (path or "").split("?")[0][:255]
    return _NUMBER.sub(":n", _UUID.sub(":id", path))


def session_id_of(request) -> str:
    """The id the screen creates at login (header X-Session-ID). Only safe characters are kept."""
    raw = ""
    if request is not None:
        raw = getattr(request, "META", {}).get("HTTP_X_SESSION_ID", "")
    return _SESSION.sub("", raw)[:40]


def _clean_trail(trail) -> list:
    clean = []
    for step in (trail or [])[-MAX_TRAIL:]:
        if isinstance(step, dict):
            clean.append({k: str(step.get(k, ""))[:200] for k in ("t", "type", "text")})
    return clean


def record_error(request, *, source, level, message, status_code=None, details="", method="", path="", screen="",
                 trail=None, user=None, session_id=""):
    """Write (or count again) one line. Returns the short code the user can read out, or "" if nothing was written."""
    try:
        if user is None and request is not None:
            candidate = getattr(request, "user", None)
            user = candidate if getattr(candidate, "is_authenticated", False) else None
        message = (message or "")[:MAX_MESSAGE]
        path = normalize_path(path) if path else ""
        key = "|".join([source, str(status_code or ""), method, path, screen[:120] if source == "frontend" else "",
                        message[:200], str(user.pk) if user else ""])
        fingerprint = hashlib.sha1(key.encode("utf-8", "replace")).hexdigest()
        now = timezone.now()
        with transaction.atomic():
            row = (ErrorLog.objects.select_for_update()
                   .filter(fingerprint=fingerprint, is_resolved=False, last_seen__gte=now - SAME_PROBLEM_WINDOW)
                   .order_by("-last_seen").first())
            if row is not None:
                row.count += 1
                row.last_seen = now
                if details:
                    row.details = details[:MAX_DETAILS]
                if trail:
                    row.trail = _clean_trail(trail)
                if session_id:
                    row.session_id = session_id
                row.save(update_fields=["count", "last_seen", "details", "trail", "session_id"])
                return row.request_code
            meta = getattr(request, "META", {}) if request is not None else {}
            row = ErrorLog.objects.create(
                last_seen=now,
                organization=user.organization if user else None,
                branch=getattr(request, "branch", None) if request is not None else None,
                user=user,
                username=(user.username if user else "")[:150],
                session_id=session_id or session_id_of(request),
                request_code=uuid.uuid4().hex[:8].upper(),
                source=source, level=level, status_code=status_code, method=method[:10], path=path,
                screen=(screen or "")[:255], message=message, details=(details or "")[:MAX_DETAILS],
                trail=_clean_trail(trail), ip_address=client_ip(request),
                user_agent=meta.get("HTTP_USER_AGENT", "")[:255], fingerprint=fingerprint,
            )
            return row.request_code
    except Exception:  # noqa: BLE001 - the log must never be the thing that breaks
        logger.exception("Could not write the error log")
        return ""
