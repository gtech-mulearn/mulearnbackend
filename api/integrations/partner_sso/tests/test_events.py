"""Spec B §3.2: events carry field names and codes, never values, URLs or secrets."""
from types import SimpleNamespace
from unittest import mock

import pytest

from api.integrations.partner_sso import events

LINK = SimpleNamespace(id="l-1")
REQUEST = SimpleNamespace(META={"REMOTE_ADDR": "10.0.0.7", "HTTP_USER_AGENT": "Firefox"})


@pytest.fixture
def create():
    with mock.patch.object(events.IntegrationAccountEvent.objects, "create") as create:
        yield create


def test_records_field_names_and_codes(create):
    events.record_event(LINK, "contact_synced", details={"fields": ["email", "phone"]})
    assert create.call_args.kwargs["details"] == {"fields": ["email", "phone"]}


def test_refuses_unknown_detail_keys(create):
    with pytest.raises(ValueError):
        events.record_event(LINK, "error", details={"email": "asha@example.com"})
    create.assert_not_called()


def test_refuses_urls_such_as_login_links(create):
    with pytest.raises(ValueError):
        events.record_event(LINK, "error", details={"partner_code": "https://partner/sso/login/abc"})
    create.assert_not_called()


def test_refuses_unknown_events(create):
    with pytest.raises(ValueError):
        events.record_event(LINK, "viewed")


def test_ip_and_user_agent_are_kept_only_as_proof_of_consent(create):
    events.record_event(LINK, "consent_granted", request=REQUEST)
    assert (create.call_args.kwargs["ip_address"], create.call_args.kwargs["user_agent"]) == ("10.0.0.7", "Firefox")
    events.record_event(LINK, "login_issued", request=REQUEST)
    assert (create.call_args.kwargs["ip_address"], create.call_args.kwargs["user_agent"]) == (None, None)
