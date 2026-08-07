import re

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
