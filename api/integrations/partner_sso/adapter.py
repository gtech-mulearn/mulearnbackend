"""What the core needs from a partner (spec B §3.8). Futuremug is the first adapter."""
from dataclasses import asdict, dataclass
from typing import Mapping, Protocol

from .subjects import Resolution, SubjectKind


class PartnerAccountNotFound(Exception):
    """update-contact: the partner has no account created by us under that email."""


class PartnerEmailInUse(Exception):
    """update-contact: the new email already belongs to another partner account."""


@dataclass(frozen=True)
class PreviewRow:
    label: str
    value: str
    note: str | None = None

    def as_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Contact:
    """What µLearn would send right now, plus the preview people agree to."""
    email: str
    first_name: str
    last_name: str | None
    phone: str | None
    organization_name: str | None
    preview: tuple = ()

    def shared_fields(self):
        names = ["email", "first_name"]
        if self.last_name:
            names.append("last_name")
        if self.phone:
            names.append("phone")
        if self.organization_name:
            names.append("organization_name")
        return names


@dataclass(frozen=True)
class ContactChange:
    new_email: str | None = None
    new_first_name: str | None = None
    new_last_name: str | None = None
    new_phone: str | None = None
    replace_contact: bool = False

    def has_changes(self):
        return bool(self.new_email or self.new_first_name or self.new_phone)

    def field_names(self):
        pairs = (("email", self.new_email), ("name", self.new_first_name), ("phone", self.new_phone))
        return [name for name, value in pairs if value]


@dataclass(frozen=True)
class ContactSnapshot:
    email: str
    first_name: str | None
    last_name: str | None
    phone: str | None


@dataclass(frozen=True)
class SessionResult:
    status: str  # "login" | "pending_approval"
    login_url: str | None = None
    expires_in: int | None = None
    pending_url: str | None = None
    message: str | None = None
    account_created: bool | None = None

    def as_response(self):
        return {key: value for key, value in asdict(self).items() if value is not None}


class PartnerAdapter(Protocol):
    provider: str
    display_name: str
    account_types: Mapping[str, SubjectKind]

    def is_enabled(self) -> bool: ...
    def rate_per_minute(self) -> int: ...
    def consent_version(self) -> str: ...
    def consent_document(self, account_type: str): ...
    def build_contact(self, account_type: str, resolution: Resolution) -> Contact: ...
    def update_contact(self, account_type: str, current_email: str, change: ContactChange) -> ContactSnapshot: ...
    def open_session(self, account_type: str, contact: Contact) -> SessionResult: ...
