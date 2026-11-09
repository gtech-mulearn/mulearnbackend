"""Request throttles for email verification (spec A §3.9)."""
from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle

from utils.permission import JWTUtils
from utils.utils import _CustomHTTPHandler


class EmailCodeIPThrottle(SimpleRateThrottle):
    """Ceiling on public code sends per client IP."""
    scope = "email_code_ip"

    def get_rate(self):
        return settings.EMAIL_CODE_IP_RATE

    def get_cache_key(self, request, view):
        ident = _CustomHTTPHandler.get_client_ip_address(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}


class EmailCodeVerifyIPThrottle(EmailCodeIPThrottle):
    """Code checks per IP: five times the send ceiling."""
    scope = "email_code_verify_ip"

    def get_rate(self):
        count, period = settings.EMAIL_CODE_IP_RATE.split("/")
        return f"{int(count) * 5}/{period}"


class EmailVerificationUserThrottle(SimpleRateThrottle):
    """Per-user ceiling for the authenticated endpoints. request.user is not
    populated by CustomizePermission, so the JWT id is the identity."""
    scope = "email_verification_user"
    rate = "30/hour"

    def get_cache_key(self, request, view):
        try:
            ident = JWTUtils.fetch_user_id(request)
        except Exception:
            return None  # unauthenticated; the permission check already refused it
        return self.cache_format % {"scope": self.scope, "ident": ident}
