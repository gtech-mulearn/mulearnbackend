"""
µLearn data → Futuremug SSO fields (spec B §3.5; partner PDF §03).

Pure functions. build_contact() feeds both the request and the consent
modal's preview, so what people agree to is exactly what is sent.
"""
import re

from api.integrations.partner_sso.adapter import Contact, PreviewRow
from api.integrations.partner_sso.errors import PartnerError
from utils.emails import normalize_email

EMAIL_MAX = 60
NAME_MAX = 25
COMPANY_NAME_MAX = 60
COLLEGE_NAME_MAX = 150
_EMAIL_RE = re.compile(r"^[a-z0-9._+\-]+@[a-z0-9.\-]+$")

SHORTENED = "Shortened to fit Futuremug's limits"
EMAIL_NOT_SUPPORTED = ("Futuremug accepts emails up to 60 characters using letters, digits and . _ + -. "
                       "Change your µLearn email to connect.")
ACCOUNT_TYPE_LABELS = {"candidate": "Candidate", "company": "Company", "college": "College"}
PERSON_LABELS = {"candidate": "Name", "company": "Contact name", "college": "Contact (TPO)"}


def futuremug_email(email):
    email = normalize_email(email)
    if len(email) > EMAIL_MAX or not _EMAIL_RE.match(email):
        raise PartnerError("email_not_supported", message=EMAIL_NOT_SUPPORTED)
    return email


def split_name(full_name):
    """First word → first_name, the rest → last_name; each at most 25 characters."""
    words = (full_name or "").split()
    if not words:
        return "", None, False
    rest = " ".join(words[1:])
    first = words[0][:NAME_MAX]
    last = rest[:NAME_MAX].rstrip() or None
    return first, last, len(words[0]) > NAME_MAX or len(rest) > NAME_MAX


def futuremug_phone(mobile):
    """(digits, note): digits only when Futuremug accepts them (10-15 after removing spaces, + and -)."""
    if not mobile:
        return None, "Not on your profile"
    digits = re.sub(r"[\s+\-]", "", mobile)
    if digits.isdigit() and 10 <= len(digits) <= 15:
        return digits, None
    return None, "Format not supported"


def _shorten(value, limit):
    value = (value or "").strip()
    if len(value) > limit:
        return value[:limit].rstrip(), True
    return value, False


def build_contact(account_type, resolution):
    person = resolution.manager
    email = futuremug_email(person.email)
    first, last, name_shortened = split_name(person.full_name)
    if not first:
        raise PartnerError("partner_rejected_field", message="Add your name to your µLearn profile to connect.")
    phone, phone_note = futuremug_phone(person.mobile)

    rows = []
    organization_name = None
    if account_type in ("company", "college"):
        limit = COMPANY_NAME_MAX if account_type == "company" else COLLEGE_NAME_MAX
        organization_name, org_shortened = _shorten(resolution.subject_name, limit)
        label = "Company name" if account_type == "company" else "College name"
        rows.append(PreviewRow(label, organization_name, SHORTENED if org_shortened else None))

    person_notes = [note for note in (
        "You, as Lead Enabler" if account_type == "college" else None,
        SHORTENED if name_shortened else None,
    ) if note]
    rows += [
        PreviewRow(PERSON_LABELS[account_type], " ".join(part for part in (first, last) if part),
                   " · ".join(person_notes) or None),
        PreviewRow("Email", email),
        PreviewRow("Phone", phone or "Not shared", phone_note),
        PreviewRow("Account type", ACCOUNT_TYPE_LABELS[account_type]),
    ]
    return Contact(email=email, first_name=first, last_name=last, phone=phone,
                   organization_name=organization_name, preview=tuple(rows))


def session_payload(account_type, contact):
    payload = {"account_type": account_type, "email": contact.email, "first_name": contact.first_name}
    if contact.last_name:
        payload["last_name"] = contact.last_name
    if contact.phone:
        payload["phone"] = contact.phone
    if account_type == "company":
        payload["company_name"] = contact.organization_name
    if account_type == "college":
        payload["college_name"] = contact.organization_name
    return payload


def update_contact_payload(account_type, current_email, change):
    payload = {"account_type": account_type, "email": current_email}
    if change.new_email:
        payload["new_email"] = change.new_email
    if change.new_phone:
        payload["new_phone"] = change.new_phone
    if change.new_first_name:
        payload["new_first_name"] = change.new_first_name
        if change.new_last_name:  # the name is replaced as a whole (PDF §06)
            payload["new_last_name"] = change.new_last_name
    if change.replace_contact:
        payload["replace_contact"] = True
    return payload
