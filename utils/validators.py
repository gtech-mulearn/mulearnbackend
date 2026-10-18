import ipaddress
import re
from urllib.parse import urlparse

from django.utils.html import escape, strip_tags
from rest_framework import serializers

SecurityValidationError = serializers.ValidationError

_SCRIPT_INJECTION_PATTERN = re.compile(
    r"<\s*script\b"
    r"|<\s*iframe\b"
    r"|<\s*object\b"
    r"|<\s*embed\b"
    r"|javascript\s*:"
    r"|vbscript\s*:"
    r"|data\s*:\s*text/html"
    r"|on\w+\s*=",
    re.IGNORECASE,
)

_SQL_INJECTION_PATTERN = re.compile(
    r"(--|#|;)"
    r"|/\*.*?\*/"
    r"|\b(union\s+select|select\s+.*\s+from|insert\s+into|update\s+.*\s+set"
    r"|delete\s+from|drop\s+table|alter\s+table|exec(ute)?\s*\(|xp_cmdshell)\b"
    r"|(\bor\b|\band\b)\s+['\"]?\s*\d+\s*=\s*\d+"
    r"|'\s*or\s*'.*'\s*=\s*'",
    re.IGNORECASE,
)

_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

_PHONE_PATTERN = re.compile(r"^\+?[0-9]{7,15}$")


def contains_script_injection(value: str) -> bool:
    return bool(_SCRIPT_INJECTION_PATTERN.search(value or ""))


def contains_sql_injection(value: str) -> bool:
    return bool(_SQL_INJECTION_PATTERN.search(value or ""))


def sanitize_html(value: str) -> str:
    return escape(strip_tags(value or ""))


def strip_control_characters(value: str) -> str:
    return _CONTROL_CHAR_PATTERN.sub("", value or "")


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def enforce_max_length(value: str, max_len: int) -> None:
    if value and len(value) > max_len:
        raise SecurityValidationError(
            f"Value exceeds maximum allowed length of {max_len} characters."
        )


def validate_safe_text(value: str) -> None:
    if contains_script_injection(value):
        raise SecurityValidationError("Value contains disallowed HTML/script content.")
    if contains_sql_injection(value):
        raise SecurityValidationError("Value contains disallowed characters or patterns.")
    if _CONTROL_CHAR_PATTERN.search(value or ""):
        raise SecurityValidationError("Value contains disallowed control characters.")


def validate_username_format(value: str) -> None:
    if not _USERNAME_PATTERN.match(value or ""):
        raise SecurityValidationError(
            "Username must be 3-32 characters long and contain only letters, "
            "numbers, underscores, hyphens, or periods."
        )


def validate_safe_filename(value: str) -> None:
    if not value or "\x00" in value:
        raise SecurityValidationError("Invalid filename.")
    if ".." in value or value.startswith("/") or value.startswith("\\") or re.match(r"^[A-Za-z]:", value):
        raise SecurityValidationError("Filename must not contain path traversal sequences.")


def validate_phone_number(value: str) -> None:
    if not _PHONE_PATTERN.match(value or ""):
        raise SecurityValidationError("Enter a valid phone number.")


# https only: these links are rendered back as clickable hrefs, so any other scheme
# (javascript:, data:, vbscript:, file:, plain http:) is rejected.
_HTTPS_URL_PATTERN = re.compile(r"^https://", re.IGNORECASE)
# The last label must be a real TLD. This also rejects the numeric host forms
# browsers still resolve as IPs (2130706433, 0x7f000001, 127.1) and single-label
# hosts such as localhost.
_TLD_PATTERN = re.compile(r"^(?:[a-z]{2,63}|xn--[a-z0-9-]{1,59})$")


def validate_safe_url(value: str, max_len: int = 500, example: str = "https://github.com/you/project") -> str:
    """
    Validate a user-supplied link that is shown to other users. Returns the trimmed
    value. Not an SSRF guard: use it only for links the server never fetches.
    """
    candidate = (value or "").strip()
    if not candidate:
        raise SecurityValidationError("Link is required.")
    enforce_max_length(candidate, max_len)
    if _CONTROL_CHAR_PATTERN.search(candidate) or any(c.isspace() for c in candidate):
        raise SecurityValidationError("Link must not contain spaces or control characters.")
    if "\\" in candidate:
        # Browsers read '\' as '/', Python's parser doesn't: the host we check and
        # the host the browser opens could differ.
        raise SecurityValidationError("Link must not contain backslashes.")
    if not _HTTPS_URL_PATTERN.match(candidate):
        raise SecurityValidationError(f"Enter a full link starting with https:// (e.g. {example}).")
    try:
        parsed = urlparse(candidate)
        hostname = parsed.hostname
    except ValueError:  # e.g. an unterminated IPv6 literal
        raise SecurityValidationError("Enter a valid link.")
    if not hostname:
        raise SecurityValidationError("Link must include a domain.")
    if parsed.username is not None or parsed.password is not None:
        raise SecurityValidationError("Link must not contain credentials.")
    try:
        ipaddress.ip_address(hostname)
        is_ip = True
    except ValueError:
        is_ip = False
    if is_ip:
        raise SecurityValidationError(f"Link must use a domain name, not an IP address (e.g. {example}).")
    if "." not in hostname or not _TLD_PATTERN.match(hostname.rsplit(".", 1)[1]):
        # localhost, intranet names, and numeric IP forms ipaddress doesn't parse (2130706433, 0x7f000001).
        raise SecurityValidationError(f"Link must use a public domain name (e.g. {example}).")
    return candidate
