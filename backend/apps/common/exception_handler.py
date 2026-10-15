"""
Friendlier error text for the screens. Everything else stays as Django REST framework sends it.
SAFE TO EDIT: the sentence below.
"""
from django.db import IntegrityError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_handler

DUPLICATE = "This already exists (the same name or code). Please use a different one."
NOT_FOUND = "This record was not found. It may have been removed, or it belongs to another branch."


def friendly_exception_handler(exc, context):
    response = drf_handler(exc, context)
    # A "must be unique" rule of the database that the screen did not check first: say it politely (not a crash)
    if response is None and isinstance(exc, IntegrityError) and "unique" in str(exc).lower():
        return Response({"detail": DUPLICATE}, status=400)
    if response is not None and response.status_code == 404:
        detail = str(response.data.get("detail", "")) if isinstance(response.data, dict) else ""
        # Django's own wording ("No Patient matches the given query.") means nothing to a clinic user
        if "matches the given query" in detail or detail in ("Not found.", ""):
            response.data = {"detail": NOT_FOUND}
    return response
