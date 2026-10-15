"""
Friendlier error text for the screens. Everything else stays as Django REST framework sends it.
SAFE TO EDIT: the sentence below.
"""
from rest_framework.views import exception_handler as drf_handler

NOT_FOUND = "This record was not found. It may have been removed, or it belongs to another branch."


def friendly_exception_handler(exc, context):
    response = drf_handler(exc, context)
    if response is not None and response.status_code == 404:
        detail = str(response.data.get("detail", "")) if isinstance(response.data, dict) else ""
        # Django's own wording ("No Patient matches the given query.") means nothing to a clinic user
        if "matches the given query" in detail or detail in ("Not found.", ""):
            response.data = {"detail": NOT_FOUND}
    return response
