"""Futuremug as a partner_sso adapter (spec B §3.5, §3.8)."""
import logging
import re

from django.conf import settings

from api.dashboard.feature.flags import is_flag_on
from api.integrations.partner_sso.adapter import ContactSnapshot, SessionResult
from api.integrations.partner_sso.subjects import SubjectKind

from . import consent, payloads
from .client import FuturemugClient

logger = logging.getLogger(__name__)

# A bearer token: printable ASCII without spaces. A stray \r or \n would make
# the HTTP layer raise with the header, and so the key, in its message.
_KEY_SHAPE = re.compile(r"[\x21-\x7e]+")


def _api_key():
    # Trimmed: env vars made from secret files often end in a newline.
    return (settings.FUTUREMUG_API_KEY or "").strip()


class FuturemugAdapter:
    provider = "futuremug"
    display_name = "Futuremug"
    account_types = {
        "candidate": SubjectKind.LEARNER,
        "company": SubjectKind.COMPANY,
        "college": SubjectKind.COLLEGE,
    }

    def is_configured(self):
        """The server has what Futuremug needs: a usable key, an https base URL and the legal links."""
        key = _api_key()
        if key and not _KEY_SHAPE.fullmatch(key):
            logger.error("FUTUREMUG_API_KEY is malformed (spaces, line breaks or non-ASCII); Futuremug stays disabled")
            return False
        return bool(
            key
            and settings.FUTUREMUG_BASE_URL.startswith("https://")
            and settings.FUTUREMUG_TERMS_URL
            and settings.FUTUREMUG_PRIVACY_URL
        )

    def is_enabled(self):
        # Configured first: it needs no cache or database round trip.
        return self.is_configured() and is_flag_on("futuremug_enabled", default=False)

    def rate_per_minute(self):
        return settings.FUTUREMUG_RATE_PER_MIN

    def consent_version(self):
        return consent.CURRENT_VERSION

    def consent_document(self, account_type):
        return consent.document(account_type)

    def build_contact(self, account_type, resolution):
        return payloads.build_contact(account_type, resolution)

    def update_contact(self, account_type, current_email, change):
        body = self._client().update_contact(payloads.update_contact_payload(account_type, current_email, change))
        return ContactSnapshot(email=body.get("email") or change.new_email or current_email,
                               first_name=body.get("first_name"), last_name=body.get("last_name"),
                               phone=body.get("phone"))

    def open_session(self, account_type, contact):
        body = self._client().session(payloads.session_payload(account_type, contact))
        return SessionResult(status=body["status"], login_url=body.get("login_url"),
                             expires_in=body.get("expires_in"), pending_url=body.get("pending_url"),
                             message=body.get("message"), account_created=body.get("account_created"))

    def _client(self):
        return FuturemugClient(settings.FUTUREMUG_BASE_URL, _api_key())


futuremug_adapter = FuturemugAdapter()
