"""Helper for the security tests: lists every URL of the API so tests can try them all."""
import uuid

from django.contrib.admindocs.views import simplify_regex
from django.urls import URLPattern, URLResolver, get_resolver

DUMMY_ID = "00000000-0000-4000-8000-000000000001"


def all_api_paths():
    """Return a sorted list of (url_with_dummy_ids, has_parameters, view_callback) for /api/v1/."""
    found = []

    def walk(patterns, prefix):
        for entry in patterns:
            if isinstance(entry, URLResolver):
                walk(entry.url_patterns, prefix + str(entry.pattern))
            elif isinstance(entry, URLPattern):
                raw = prefix + str(entry.pattern)
                if "format" in raw or "\\." in raw:  # ".json" style suffixes: same views again
                    continue
                path = simplify_regex(raw)
                has_params = "<" in path
                import re

                path = re.sub(r"<[^>]+>", DUMMY_ID, path)
                if not path.startswith("/api/v1/"):
                    continue
                if not path.endswith("/"):
                    path += "/"
                found.append((path, has_params, entry.callback))

    walk(get_resolver().url_patterns, "")
    unique = {}
    for path, has_params, callback in found:
        unique.setdefault(path, (path, has_params, callback))
    return sorted(unique.values(), key=lambda item: item[0])
