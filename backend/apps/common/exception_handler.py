"""
Friendlier error text for the screens. Everything else stays as Django REST framework sends it.
SAFE TO EDIT: the sentence below.
"""
import logging
import traceback

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DataError, IntegrityError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

DUPLICATE = "This already exists (the same name or code). Please use a different one."
CRASH = "Something went wrong on the server. It has been written to the Error log. Code: {code}."
# Which refused / failed answers go to the Error log, and how serious they are (401 is only an expired login: not logged)
LOGGED_STATUS = {400: "notice", 404: "notice", 405: "notice", 409: "notice", 413: "notice", 415: "notice",
                 403: "warning", 429: "warning"}
logger = logging.getLogger(__name__)
NOT_FOUND = "This record was not found. It may have been removed, or it belongs to another branch."


def _friendly(exc, context):
    response = drf_handler(exc, context)
    # A "must be unique" rule of the database that the screen did not check first: say it politely (not a crash)
    if response is None and isinstance(exc, IntegrityError) and "unique" in str(exc).lower():
        return Response({"detail": DUPLICATE}, status=400)
    # A wrong value typed into a filter or link (for example an id that is not an id) is a mistake of the person, not a crash
    if response is None and isinstance(exc, DjangoValidationError):
        return Response({"detail": " ".join(exc.messages) or "This value is not valid."}, status=400)
    if response is None and (isinstance(exc, DataError) or isinstance(exc, ValueError)) and (
            "NUL" in str(exc) or "null character" in str(exc).lower() or "0x00" in str(exc)):
        return Response({"detail": "The text contains a character that is not allowed."}, status=400)
    if response is not None and response.status_code == 404:
        detail = str(response.data.get("detail", "")) if isinstance(response.data, dict) else ""
        # Django's own wording ("No Patient matches the given query.") means nothing to a clinic user
        if "matches the given query" in detail or detail in ("Not found.", ""):
            response.data = {"detail": NOT_FOUND}
    return response


def _plain(value) -> str:
    """Plain words from an error answer: {"date": [ErrorDetail("Already booked")]} -> "date: Already booked"."""
    if isinstance(value, dict):
        return "; ".join(f"{key}: {_plain(item)}" if key != "detail" else _plain(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(_plain(item) for item in value)
    return str(value)


def _message_of(data) -> str:
    if isinstance(data, dict) and isinstance(data.get("detail"), str):
        return data["detail"]
    return _plain(data)


def friendly_exception_handler(exc, context):
    """Friendly text for the screens, and every failure written to the Error log (apps/audit/error_log.py)."""
    from apps.audit.error_log import record_error, request_facts  # imported here: this file loads before the apps are ready

    response = _friendly(exc, context)
    request = context.get("request")
    path = getattr(request, "path", "") or ""
    if path.startswith("/api/v1/error-logs/report"):
        return response  # a problem while reporting a problem is never reported again
    user = getattr(request, "user", None)
    known_user = bool(getattr(user, "is_authenticated", False))
    method = getattr(request, "method", "") or ""
    if response is None:
        logger.error("Unhandled error on %s %s", method, path, exc_info=exc)
        code = record_error(
            request, source="backend", level="error", status_code=500, method=method, path=path,
            message=f"{type(exc).__name__}: {exc}",
            details="".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
            extra={**request_facts(request), "exception": f"{type(exc).__module__}.{type(exc).__name__}"},
        )
        return Response({"detail": CRASH.format(code=code or "-"), "code": code}, status=500)
    if known_user and response.status_code in LOGGED_STATUS:
        record_error(request, source="backend", level=LOGGED_STATUS[response.status_code], status_code=response.status_code,
                     method=method, path=path, message=_message_of(response.data),
                     extra={**request_facts(request), "server_answer": response.data})
    return response
