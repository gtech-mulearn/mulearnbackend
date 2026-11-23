"""Helpers for characterization tests: pin a legacy route's behaviour before it moves (issue 0025).

See docs/architecture/12-testing-and-quality-gates.md. The fixtures in conftest.py wrap these.
"""

import difflib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from django.conf import settings

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
ENVELOPE_KEYS = ("hasError", "statusCode", "message", "response")

_UUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
# The envelope's requestId (building_blocks.observability): "req_" and a UUIDv7's 32 hex digits.
_REQUEST_ID = re.compile(r"req_[0-9a-f]{32}")
# An ISO 8601 date and time, with optional fractions and offset. A bare date isn't replaced.
_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?")


def mint_token(user, roles, expires_in_seconds: int = 3600) -> str:
    """An access token for ``user``, signed and shaped the way utils/permission.py validates it."""
    expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
    payload = {
        "id": str(user.id),
        "muid": user.muid,
        "roles": list(roles),
        "expiry": expiry.strftime("%Y-%m-%d %H:%M:%S%z"),
        "tokenType": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def envelope_problems(response, *, has_error: bool, status_code: int, http_status: int) -> list[str]:
    """What differs from the legacy envelope expected; an empty list when it matches."""
    body = response.json()
    problems = [f"missing key {key!r}" for key in ENVELOPE_KEYS if key not in body]
    if body.get("hasError") is not has_error:
        problems.append(f"hasError is {body.get('hasError')!r}, expected {has_error!r}")
    if body.get("statusCode") != status_code:
        problems.append(f"statusCode is {body.get('statusCode')!r}, expected {status_code!r}")
    if response.status_code != http_status:
        problems.append(f"HTTP status is {response.status_code}, expected {http_status}")
    return problems


def normalise(value):
    """Replace values that change on every run, ids and timestamps, with placeholders.

    Only whole string values are replaced. Keys, types, nulls, numbers and list order are kept,
    so any change to the shape of a response still shows.
    """
    if isinstance(value, dict):
        return {key: normalise(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalise(item) for item in value]
    if isinstance(value, str):
        if _UUID.fullmatch(value):
            return "<uuid>"
        if _REQUEST_ID.fullmatch(value):
            return "<request-id>"
        if _DATETIME.fullmatch(value):
            return "<datetime>"
    return value


def _dump(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def check_golden(body, path: Path, *, update: bool) -> None:
    """Compare the normalised ``body`` with the golden file at ``path``; with ``update``, rewrite it."""
    actual = normalise(body)
    if update:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dump(actual), encoding="utf-8", newline="\n")
        return
    if not path.exists():
        raise AssertionError(f"No golden file {path.name}. Run with --update-golden to create it, then review it.")
    expected = json.loads(path.read_text(encoding="utf-8"))
    if actual != expected:
        before, after = _dump(expected).splitlines(True), _dump(actual).splitlines(True)
        diff = "".join(difflib.unified_diff(before, after, "golden", "actual"))
        raise AssertionError(
            f"The response differs from {path.name}. If the change is intended, run with --update-golden.\n{diff}"
        )
