"""URL field validation on EventWriteSerializer.

These call the field validators directly — no DB, no request cycle — because
what is under test is the rule and, just as importantly, the message. A user
who leaves the scheme off has to be told that is what went wrong.
"""
import pytest
from rest_framework import serializers

from api.dashboard.events.serializers import EventWriteSerializer


def _error(method, value):
    """Run one field validator and return its message, or None if accepted."""
    try:
        getattr(EventWriteSerializer(), method)(value)
        return None
    except serializers.ValidationError as exc:
        return " ".join(str(d) for d in exc.detail)


# ─────────────────────────────────────────────────────────────
# registration_url
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value", [
    "https://mulearn.org/register",
    "http://mulearn.org/register",
])
def test_registration_url_accepts_a_full_link(value):
    assert _error("validate_registration_url", value) is None


@pytest.mark.parametrize("value", ["", None])
def test_registration_url_accepts_empty(value):
    assert _error("validate_registration_url", value) is None


def test_registration_url_rejects_a_link_without_a_scheme():
    assert _error("validate_registration_url", "mulearn.org/register") is not None


def test_registration_url_error_tells_the_user_to_add_https():
    message = _error("validate_registration_url", "mulearn.org/register")
    assert "https://" in message


def test_registration_url_rejects_text_that_is_not_a_link():
    assert _error("validate_registration_url", "jbjbjhjb") is not None


# ─────────────────────────────────────────────────────────────
# venue_online_link
# ─────────────────────────────────────────────────────────────

def test_online_link_accepts_a_full_link():
    assert _error("validate_venue_online_link", "https://meet.google.com/abc") is None


@pytest.mark.parametrize("value", ["", None])
def test_online_link_accepts_empty(value):
    assert _error("validate_venue_online_link", value) is None


def test_online_link_rejects_a_link_without_a_scheme():
    assert _error("validate_venue_online_link", "meet.google.com/abc") is not None


def test_online_link_error_tells_the_user_to_add_https():
    message = _error("validate_venue_online_link", "meet.google.com/abc")
    assert "https://" in message


# ─────────────────────────────────────────────────────────────
# venue_maps_url — the specific message is currently swallowed
# ─────────────────────────────────────────────────────────────

def test_maps_url_accepts_a_google_maps_link():
    assert _error("validate_venue_maps_url", "https://maps.google.com/x") is None


def test_maps_url_missing_scheme_says_to_add_https():
    """The raise sat inside a try whose `except Exception` caught its own
    ValidationError, replacing this with a bare 'Enter a valid URL.'"""
    message = _error("validate_venue_maps_url", "maps.google.com/x")
    assert "https://" in message


def test_maps_url_still_rejects_a_non_google_host():
    message = _error("validate_venue_maps_url", "https://example.com/x")
    assert "Google Maps" in message
