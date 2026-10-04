"""Limits on how often someone may try to log in (stops password guessing)."""
from rest_framework.throttling import SimpleRateThrottle

from apps.common.utils import client_ip


class LoginIPThrottle(SimpleRateThrottle):
    """Limit login attempts from one computer (IP address)."""

    scope = "login_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": client_ip(request) or "unknown"}


class LoginUserThrottle(SimpleRateThrottle):
    """Limit login attempts for one username, from any computer."""

    scope = "login_user"

    def get_cache_key(self, request, view):
        username = str(request.data.get("username", "")).strip().lower()
        if not username:
            return None
        return self.cache_format % {"scope": self.scope, "ident": username}


class OtpThrottle(SimpleRateThrottle):
    scope = "otp"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": client_ip(request) or "unknown"}
