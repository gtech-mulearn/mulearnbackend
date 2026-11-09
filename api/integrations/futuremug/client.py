"""
Futuremug SSO HTTP client (spec B §3.5-§3.6; partner PDF §01, §05-§07).

Server-to-server only. The key comes from settings and never appears in a
log, an event or a response; neither do request bodies or URLs.
"""
import logging
import re
import time
from urllib.parse import urlsplit

import requests

from api.integrations.partner_sso.adapter import PartnerAccountNotFound, PartnerEmailInUse
from api.integrations.partner_sso.errors import PartnerError

logger = logging.getLogger(__name__)

TIMEOUT = (3, 10)  # (connect, read) seconds
SESSION_PATH = "/v1/api/sso/session"
UPDATE_CONTACT_PATH = "/v1/api/sso/update-contact"
_KEY_OR_CONFIG_CODES = frozenset({"https_required", "client_disabled", "ip_not_allowed", "account_type_not_allowed"})
_SESSION_STATUSES = frozenset({"login", "pending_approval"})


class FuturemugClient:
    def __init__(self, base_url, api_key, session=None, sleep=time.sleep):
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._http = session or requests.Session()
        self._sleep = sleep
        self._host = urlsplit(self.base_url).hostname

    def session(self, payload):
        body = self._post(SESSION_PATH, payload, "session")
        if body.get("status") not in _SESSION_STATUSES:
            logger.error("futuremug session returned an unexpected status")
            raise PartnerError("partner_unavailable", http_status=502, partner_code="bad_status")
        if body["status"] == "login" and not self._is_partner_url(body.get("login_url")):
            logger.error("futuremug session returned a login link for an unexpected host")
            raise PartnerError("partner_unavailable", http_status=502, partner_code="bad_login_url")
        if body.get("pending_url") and not self._is_partner_url(body["pending_url"]):
            body = {**body, "pending_url": None}
        return body

    def update_contact(self, payload):
        return self._post(UPDATE_CONTACT_PATH, payload, "update_contact")

    # ── Transport ───────────────────────────────────────────────────────

    def _post(self, path, payload, stage):
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        started = time.monotonic()
        response = None
        for attempt in (1, 2):
            try:
                response = self._http.post(f"{self.base_url}{path}", json=payload, headers=headers, timeout=TIMEOUT)
            except requests.ConnectionError:  # includes ConnectTimeout: safe to retry once
                if attempt == 1:
                    self._sleep(0.5)
                    continue
                self._log(stage, None, "connection_error", started)
                raise PartnerError("partner_unavailable", http_status=503, partner_code="connection_error", retryable=True)
            except requests.Timeout:  # a read timeout may have done the work: do not retry
                self._log(stage, None, "timeout", started)
                raise PartnerError("partner_unavailable", http_status=503, partner_code="timeout", retryable=True)
            except (requests.RequestException, ValueError) as exc:
                # Anything else, e.g. a malformed header from a bad key. Its message
                # can quote the headers (the key), so only its class name is logged,
                # and the chain is dropped so no traceback carries it either.
                logger.error("futuremug %s request failed: %s", stage, type(exc).__name__)
                raise PartnerError("partner_unavailable", http_status=502, partner_code="request_error") from None
            if response.status_code == 503 and attempt == 1:
                self._sleep(0.5)
                continue
            break
        body = self._json(response)
        error = body.get("error") if isinstance(body.get("error"), dict) else {}
        code = _safe_code(error.get("code"))
        self._log(stage, response.status_code, code, started)
        if response.status_code == 200 and body.get("success") is True:
            return body
        message = error.get("message")
        raise self._map_error(stage, response.status_code, code, message if isinstance(message, str) else None)

    def _map_error(self, stage, http_status, code, partner_message):
        if http_status == 404 and code == "account_not_found":
            return PartnerAccountNotFound()
        if stage == "update_contact" and http_status == 409 and code == "email_in_use":
            return PartnerEmailInUse()
        if http_status == 400:
            return PartnerError("partner_rejected_field", partner_code=code)
        if http_status == 401 or (http_status == 403 and code in _KEY_OR_CONFIG_CODES):
            logger.error("futuremug %s refused our key or configuration: %s", stage, code)
            return PartnerError("partner_unavailable", http_status=502, partner_code=code)
        if http_status == 403:
            return PartnerError("partner_account_blocked", partner_code=code)
        if http_status == 409:
            return PartnerError("partner_conflict", partner_code=code, message=_conflict_text(partner_message))
        if http_status == 429:
            return PartnerError("partner_busy", partner_code=code, retry_after=60)
        return PartnerError("partner_unavailable", http_status=503, partner_code=code or f"http_{http_status}",
                            retryable=True)

    def _is_partner_url(self, url):
        parts = urlsplit(url or "")
        return parts.scheme == "https" and parts.hostname == self._host

    @staticmethod
    def _json(response):
        try:
            body = response.json()
        except ValueError:
            return {}
        return body if isinstance(body, dict) else {}

    @staticmethod
    def _log(stage, http_status, code, started):
        logger.info("futuremug %s http=%s code=%s ms=%d", stage, http_status, code,
                    int((time.monotonic() - started) * 1000))


def _safe_code(value):
    """The partner's error code as a short, inert token: it reaches logs, events and responses."""
    if value is None:
        return None
    return re.sub(r"[^A-Za-z0-9_.\-]", "", str(value))[:40] or "unknown"


def _conflict_text(partner_message):
    """The partner's words, as plain short text, plus what to do. None means use our default."""
    text = re.sub(r"\s+", " ", partner_message or "").strip()[:300].rstrip()
    if not text:
        return None
    return f"{text} Contact Futuremug support if this is your account."
