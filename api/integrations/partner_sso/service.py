"""
Partner SSO orchestration (spec B §3.4): status, authorize, sign in, disconnect.

Provider-agnostic: everything partner-specific arrives through the adapter;
who may act, consent and audit live here.
"""
import logging

from django.db import IntegrityError
from django.utils import timezone

from api.email_verification.service import is_email_verified
from db.integrations import IntegrationAccountLink
from utils.emails import normalize_email

from . import events, ratelimit
from .adapter import ContactChange, PartnerAccountNotFound, PartnerEmailInUse
from .errors import PartnerError
from .subjects import resolve

logger = logging.getLogger(__name__)

# A sign-in makes up to three partner calls (conflict, reconcile, session), each
# up to two attempts of 3 s connect + 10 s read: about 80 s. The per-link lock
# must outlive that, or a disconnect could slip in mid-sign-in (spec B §3.7).
LINK_LOCK_SECONDS = 90


# ── Public API ─────────────────────────────────────────────────────────────

def connection_status(adapter, account_type, user):
    if not adapter.is_enabled():
        return {"enabled": False, "account_type": account_type}
    resolution = resolve(adapter.account_types[account_type], user.id)
    link = _get_link(adapter, resolution) if resolution.subject_id else None
    eligibility = {"eligible": resolution.can_manage, "reason": resolution.reason, "message": resolution.message}
    preview = None
    if resolution.can_manage:
        try:
            preview = [row.as_dict() for row in adapter.build_contact(account_type, resolution).preview]
        except PartnerError as error:
            eligibility = {"eligible": False, "reason": error.code, "message": error.text(adapter.display_name)}
    return {
        "enabled": True,
        "account_type": account_type,
        "hidden": resolution.hidden,
        "eligibility": eligibility,
        "can_manage": resolution.can_manage,
        "managed_by": None if resolution.can_manage else getattr(resolution.manager, "full_name", None),
        "email_verified": is_email_verified(user),
        "connection": _connection(link, user, resolution),
        "consent": {
            "current_version": adapter.consent_version(),
            "accepted_version": link.consent_version if link else None,
            "needs_consent": bool(resolution.can_manage and _needs_consent(adapter, link, user)),
            "document": adapter.consent_document(account_type).as_dict() if resolution.can_manage else None,
        },
        "shared_data_preview": preview,
    }


def authorize(adapter, account_type, user, *, consent_version, accepted, request=None):
    resolution = _require_manager(adapter, account_type, user)
    if accepted is not True or consent_version != adapter.consent_version():
        raise PartnerError("consent_version_mismatch")
    contact = adapter.build_contact(account_type, resolution)  # an unusable email fails before consent
    link = _get_link(adapter, resolution) or _new_link(adapter, account_type, resolution)
    link.consent_version = consent_version
    link.consented_at = _now()
    link.consented_by_id = user.id
    link.disconnected_at = None
    link.disconnected_by_id = None
    if link.status not in ("active", "pending_approval"):
        link.status = "consented"
    _save(link)
    events.record_event(link, "consent_granted", actor=user, consent_version=consent_version,
                        details={"fields": contact.shared_fields()}, request=request)
    return _sign_in(adapter, account_type, user, resolution)


def sign_in(adapter, account_type, user):
    resolution = _require_manager(adapter, account_type, user)
    link = _get_link(adapter, resolution)
    if _needs_consent(adapter, link, user):
        raise PartnerError("consent_required")
    return _sign_in(adapter, account_type, user, resolution)


def disconnect(adapter, account_type, user, *, request=None):
    """Withdrawing consent is as easy as giving it: no email check, no partner call."""
    resolution = resolve(adapter.account_types[account_type], user.id)
    if not resolution.can_manage:
        raise PartnerError("not_eligible", reason=resolution.reason)
    # Under the link's lock, so a sign-in in flight can't write the link back
    # over the withdrawal; that sign-in answers in_progress, or this one does.
    with _lock(adapter, resolution.subject_type, resolution.subject_id):
        link = _get_link(adapter, resolution)
        if link is not None and link.status != "disconnected":
            link.status = "disconnected"
            link.disconnected_at = _now()
            link.disconnected_by_id = user.id
            link.consent_version = link.consented_at = link.consented_by_id = None
            # external_email stays: the partner account still exists under it (spec B §3.2).
            link.synced_first_name = link.synced_last_name = link.synced_phone = None
            _save(link)
            events.record_event(link, "disconnected", actor=user, request=request)
    return {"status": "disconnected"}


# ── The sequence (spec B §3.4 steps 2-7) ─────────────────────────────────

def _require_manager(adapter, account_type, user):
    if not adapter.is_enabled():
        raise PartnerError("feature_disabled")
    resolution = resolve(adapter.account_types[account_type], user.id)
    if not resolution.can_manage:
        raise PartnerError("not_eligible", reason=resolution.reason)
    if not is_email_verified(user):
        raise PartnerError("email_unverified")
    retry_after = ratelimit.take_actor_attempt(adapter.provider, user.id)
    if retry_after:
        raise PartnerError("rate_limited", retry_after=retry_after)
    return resolution


def _needs_consent(adapter, link, user):
    """Consent is personal: a newcomer never rides on a predecessor's consent."""
    return (link is None or link.status == "disconnected"
            or link.consent_version != adapter.consent_version()
            or link.consented_by_id != user.id)


def _sign_in(adapter, account_type, user, resolution):
    with _lock(adapter, resolution.subject_type, resolution.subject_id):
        # Re-read under the lock: a disconnect may have landed since the caller
        # looked, and acting on the stale copy would restore withdrawn consent.
        link = _get_link(adapter, resolution)
        if _needs_consent(adapter, link, user):
            raise PartnerError("consent_required")
        contact = adapter.build_contact(account_type, resolution)
        try:
            _resolve_conflicts(adapter, link, contact)
            _reconcile(adapter, account_type, user, link, contact)
            result = _budgeted(adapter, lambda: adapter.open_session(account_type, contact))
        except PartnerError as error:
            _record_failure(link, user, error)
            raise
        _apply_session(link, user, contact, result)
        return result.as_response()


def _lock(adapter, subject_type, subject_id):
    return ratelimit.link_lock(adapter.provider, f"{subject_type}:{subject_id}", timeout=LINK_LOCK_SECONDS)


def _budgeted(adapter, call):
    retry_after = ratelimit.take_partner_call(adapter.provider, adapter.rate_per_minute())
    if retry_after:
        raise PartnerError("partner_busy", retry_after=retry_after)
    return call()


def _resolve_conflicts(adapter, link, contact):
    """Step 4: never let two µLearn subjects share one partner account."""
    other = _conflicting_link(adapter, link, contact.email)
    if other is None:
        return
    # The other subject's link is written too, so it is locked and re-read like ours.
    with _lock(adapter, other.subject_type, other.subject_id):
        other = _conflicting_link(adapter, link, contact.email)
        if other is None:
            return
        owner = other.contact_user
        if (other.status == "disconnected" or owner is None or not is_email_verified(owner)
                or normalize_email(owner.email) == normalize_email(contact.email)):
            raise PartnerError("email_in_use_by_other_link")
        try:
            snapshot = _budgeted(adapter, lambda: adapter.update_contact(
                other.account_type, other.external_email, ContactChange(new_email=normalize_email(owner.email))))
        except PartnerAccountNotFound:
            other.external_email = None  # never really a partner account of ours: free the address
            _save(other)
            return
        except PartnerEmailInUse:
            raise PartnerError("email_in_use_by_other_link")
        _store_snapshot(other, snapshot, other.contact_user_id)
        events.record_event(other, "contact_synced", details={"fields": ["email"]})


def _reconcile(adapter, account_type, user, link, contact):
    """Step 5: update-contact BEFORE /session, or a new email creates a duplicate account."""
    if not link.external_email:
        return
    takeover = link.contact_user_id is not None and link.contact_user_id != user.id
    change = _contact_change(link, contact, takeover)
    if change is None:
        return
    previous_contact = link.contact_user_id
    try:
        snapshot = _budgeted(adapter, lambda: adapter.update_contact(account_type, link.external_email, change))
    except PartnerAccountNotFound:
        events.record_event(link, "error", actor=user,
                            details={"stage": "update_contact", "partner_code": "account_not_found"})
        link.external_email = None
        _save(link)
        return
    except PartnerEmailInUse:
        events.record_event(link, "error", actor=user,
                            details={"stage": "update_contact", "partner_code": "email_in_use"})
        return
    _store_snapshot(link, snapshot, user.id)
    if change.replace_contact:
        events.record_event(link, "contact_replaced", actor=user,
                            details={"fields": change.field_names(), "previous_contact_user_id": previous_contact})
    else:
        events.record_event(link, "contact_synced", actor=user, details={"fields": change.field_names()})


def _contact_change(link, contact, takeover):
    if takeover:
        return ContactChange(new_email=contact.email, new_first_name=contact.first_name,
                             new_last_name=contact.last_name, new_phone=contact.phone, replace_contact=True)
    name_changed = (contact.first_name, contact.last_name) != (link.synced_first_name, link.synced_last_name)
    change = ContactChange(
        new_email=contact.email if normalize_email(contact.email) != normalize_email(link.external_email) else None,
        new_first_name=contact.first_name if name_changed else None,
        new_last_name=contact.last_name if name_changed else None,
        # The partner cannot remove a phone, so a removed phone is simply not sent.
        new_phone=contact.phone if contact.phone and contact.phone != link.synced_phone else None,
    )
    return change if change.has_changes() else None


def _apply_session(link, user, contact, result):
    link.external_email = contact.email
    link.synced_first_name = contact.first_name
    link.synced_last_name = contact.last_name
    link.synced_phone = contact.phone
    link.contact_user_id = user.id
    link.last_error_code = None
    if result.status == "login":
        link.status = "active"
        link.last_login_at = _now()
    else:
        link.status = "pending_approval"
    _save(link)
    events.record_event(link, "login_issued" if result.status == "login" else "pending_approval",
                        actor=user, details={"account_created": result.account_created})


def _store_snapshot(link, snapshot, contact_user_id):
    link.external_email = snapshot.email
    link.synced_first_name = snapshot.first_name
    link.synced_last_name = snapshot.last_name
    link.synced_phone = snapshot.phone
    link.contact_user_id = contact_user_id
    link.last_synced_at = _now()
    link.last_error_code = None
    _save(link)


def _record_failure(link, user, error):
    link.last_error_code = (error.partner_code or error.code)[:40]
    if error.code == "partner_account_blocked":
        link.status = "rejected" if error.partner_code == "account_rejected" else "blocked"
    _save(link)
    events.record_event(link, "error", actor=user,
                        details={"partner_code": error.partner_code or error.code, "http_status": error.http_status})


def _connection(link, user, resolution):
    if link is None:
        return None
    return {
        "status": link.status,
        "connected_at": link.consented_at,
        "last_login_at": link.last_login_at,
        "contact_name": getattr(link.contact_user, "full_name", None),
        "takeover_required": bool(resolution.can_manage and link.status != "disconnected"
                                  and link.contact_user_id and link.contact_user_id != user.id),
    }


# ── Persistence: small, so tests can patch them ───────────────────────────

def _now():
    return timezone.now().replace(microsecond=0)


def _get_link(adapter, resolution):
    return (IntegrationAccountLink.objects.select_related("contact_user")
            .filter(provider=adapter.provider, subject_type=resolution.subject_type,
                    subject_id=resolution.subject_id).first())


def _new_link(adapter, account_type, resolution):
    return IntegrationAccountLink(provider=adapter.provider, account_type=account_type,
                                  subject_type=resolution.subject_type, subject_id=resolution.subject_id,
                                  status="consented")


def _conflicting_link(adapter, link, email):
    return (IntegrationAccountLink.objects.select_related("contact_user")
            .filter(provider=adapter.provider, external_email__iexact=email)
            .exclude(id=link.id).first())


def _save(link):
    try:
        link.save()
    except IntegrityError:
        # The unique external_email key caught a race that the conflict check missed.
        raise PartnerError("email_in_use_by_other_link")
