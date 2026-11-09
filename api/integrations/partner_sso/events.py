"""Append-only audit of partner links (spec B §3.2). Never values, URLs or secrets."""
from db.integrations import IntegrationAccountEvent
from utils.utils import _CustomHTTPHandler

EVENTS = frozenset({
    "consent_granted", "login_issued", "pending_approval",
    "contact_synced", "contact_replaced", "disconnected", "error",
})
DETAIL_KEYS = frozenset({
    "fields", "account_created", "stage", "http_status", "partner_code", "previous_contact_user_id",
})
_PROOF_OF_CONSENT = frozenset({"consent_granted", "disconnected"})


def record_event(link, event, *, actor=None, consent_version=None, details=None, request=None):
    if event not in EVENTS:
        raise ValueError(f"unknown event {event!r}")
    details = {key: value for key, value in (details or {}).items() if value is not None}
    unknown = set(details) - DETAIL_KEYS
    if unknown:
        raise ValueError(f"event details may not carry {sorted(unknown)}")
    if any(isinstance(value, str) and "://" in value for value in details.values()):
        raise ValueError("URLs (such as login links) never go into events")
    ip_address = user_agent = None
    if request is not None and event in _PROOF_OF_CONSENT:
        ip_address = _CustomHTTPHandler.get_client_ip_address(request)
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:255] or None
    return IntegrationAccountEvent.objects.create(
        link=link, event=event, actor_user=actor, consent_version=consent_version,
        details=details or None, ip_address=ip_address, user_agent=user_agent,
    )
