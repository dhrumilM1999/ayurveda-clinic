"""
Extra safety for every response, and a login limit for the Django admin page.
ASK FIRST before editing: wrong values here can break the screens or weaken security.
"""
import re

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse

from .utils import client_ip

# The API only sends data (JSON): nothing on it may load scripts, pictures or be shown inside another page.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
# The Django admin site needs its own styles and a few inline scripts.
ADMIN_CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
             "script-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()"


class SecurityHeadersMiddleware:
    """Adds Content-Security-Policy, Permissions-Policy and 'do not cache' to API answers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        path = request.path
        response.headers.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        if path.startswith("/api/"):
            # Patient data must never be kept by a browser cache, a proxy or a shared PC.
            if "public" not in response.headers.get("Cache-Control", ""):  # only the clinic logo is meant to be cached
                response.headers["Cache-Control"] = "no-store, private"
                response.headers["Pragma"] = "no-cache"
            if (response.headers.get("Content-Type") or "").startswith("application/json"):
                response.headers.setdefault("Content-Security-Policy", API_CSP)
            # Every API answer: never shown inside another site's frame
            response.headers.setdefault("Content-Security-Policy", "frame-ancestors 'none'")
        elif path.startswith("/" + settings.ADMIN_URL):
            response.headers.setdefault("Content-Security-Policy", ADMIN_CSP)
            response.headers["Cache-Control"] = "no-store, private"
        else:
            response.headers.setdefault("Content-Security-Policy", API_CSP)
        return response


class AdminLoginLimitMiddleware:
    """Stops password guessing on the Django admin login page: 10 tries a minute per computer."""

    LIMIT = 10
    WINDOW_SECONDS = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path.rstrip("/") == "/" + settings.ADMIN_URL + "login":
            key = "adminlogin:" + re.sub(r"[^0-9a-fA-F:.]", "", client_ip(request) or "unknown")
            cache.add(key, 0, self.WINDOW_SECONDS)
            try:
                tries = cache.incr(key)
            except ValueError:
                cache.set(key, 1, self.WINDOW_SECONDS)
                tries = 1
            if tries > self.LIMIT:
                return HttpResponse("Too many login attempts. Please wait a minute and try again.", status=429)
        return self.get_response(request)
