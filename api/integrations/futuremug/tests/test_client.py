"""Spec B §3.5-§3.6: transport, error mapping, and nothing secret in the logs."""
import logging

import pytest
import requests

from api.integrations.futuremug.client import SESSION_PATH, TIMEOUT, FuturemugClient
from api.integrations.partner_sso.adapter import PartnerAccountNotFound, PartnerEmailInUse
from api.integrations.partner_sso.errors import PartnerError

BASE = "https://newdev.futuremug.com"
KEY = "fmsso_test_secret_key"
LOGIN = {"success": True, "status": "login", "account_type": "candidate", "account_created": True,
         "login_url": "https://newdev.futuremug.com/sso/login/5f0c", "expires_in": 120}


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


class FakeHTTP:
    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def post(self, url, json, headers, timeout):
        self.requests.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make(*outcomes):
    http = FakeHTTP(*outcomes)
    return FuturemugClient(BASE, KEY, session=http, sleep=lambda seconds: None), http


def failure(status, code, message="Partner says no"):
    return FakeResponse(status, {"success": False, "error": {"code": code, "message": message}})


def test_session_sends_the_key_as_a_bearer_with_json_and_timeouts():
    client, http = make(FakeResponse(200, LOGIN))
    assert client.session({"account_type": "candidate"})["login_url"] == LOGIN["login_url"]
    sent = http.requests[0]
    assert sent["url"] == BASE + SESSION_PATH
    assert sent["headers"]["Authorization"] == f"Bearer {KEY}"
    assert sent["timeout"] == TIMEOUT


def test_pending_approval_passes_through_but_a_foreign_pending_url_is_dropped():
    body = {"success": True, "status": "pending_approval", "login_url": None,
            "pending_url": "https://evil.example/pending", "message": "Awaiting approval"}
    client, _ = make(FakeResponse(200, body))
    result = client.session({})
    assert result["status"] == "pending_approval" and result["pending_url"] is None


@pytest.mark.parametrize("login_url", ["https://evil.example/sso/login/x", "http://newdev.futuremug.com/sso/login/x"])
def test_a_login_url_off_the_partner_host_or_not_https_is_refused(login_url):
    client, _ = make(FakeResponse(200, {**LOGIN, "login_url": login_url}))
    with pytest.raises(PartnerError) as error:
        client.session({})
    assert (error.value.code, error.value.http_status, error.value.partner_code) == ("partner_unavailable", 502, "bad_login_url")


def test_an_unknown_session_status_is_refused():
    client, _ = make(FakeResponse(200, {"success": True, "status": "error"}))
    with pytest.raises(PartnerError) as error:
        client.session({})
    assert error.value.code == "partner_unavailable"


@pytest.mark.parametrize("status,code,expected,http_status", [
    (400, "invalid_name", "partner_rejected_field", 422),
    (401, "unauthorized", "partner_unavailable", 502),
    (403, "client_disabled", "partner_unavailable", 502),
    (403, "account_blocked", "partner_account_blocked", 403),
    (409, "email_in_use", "partner_conflict", 409),
    (429, "rate_limited", "partner_busy", 429),
    (500, "server_error", "partner_unavailable", 503),
])
def test_errors_map_to_clear_codes(status, code, expected, http_status):
    client, _ = make(failure(status, code), failure(status, code))
    with pytest.raises(PartnerError) as error:
        client.session({})
    assert (error.value.code, error.value.http_status, error.value.partner_code) == (expected, http_status, code)


def test_a_conflict_shows_the_partners_words_plainly_and_briefly():
    client, _ = make(failure(409, "account_exists", "  An account with this email\nalready exists. " + "x" * 400))
    with pytest.raises(PartnerError) as error:
        client.session({})
    text = error.value.text("Futuremug")
    assert text.startswith("An account with this email already exists.")
    assert len(text) <= 360 and "Contact Futuremug support" in text


def test_update_contact_404_means_not_one_of_our_accounts():
    client, _ = make(failure(404, "account_not_found"))
    with pytest.raises(PartnerAccountNotFound):
        client.update_contact({})


def test_update_contact_409_means_the_new_email_is_taken():
    client, _ = make(failure(409, "email_in_use"))
    with pytest.raises(PartnerEmailInUse):
        client.update_contact({})


def test_one_retry_on_503_then_success():
    client, http = make(failure(503, "temporarily_unavailable"), FakeResponse(200, LOGIN))
    assert client.session({})["status"] == "login"
    assert len(http.requests) == 2


def test_connection_errors_retry_once_then_fail():
    client, http = make(requests.ConnectionError("down"), requests.ConnectionError("down"))
    with pytest.raises(PartnerError) as error:
        client.session({})
    assert error.value.code == "partner_unavailable" and len(http.requests) == 2


def test_read_timeouts_do_not_retry():
    client, http = make(requests.ReadTimeout("slow"))
    with pytest.raises(PartnerError):
        client.session({})
    assert len(http.requests) == 1


def test_a_non_json_error_body_is_handled():
    client, _ = make(FakeResponse(502, ValueError("not json")), FakeResponse(502, ValueError("not json")))
    with pytest.raises(PartnerError) as error:
        client.session({})
    assert error.value.code == "partner_unavailable"


def test_the_key_and_urls_never_reach_the_logs(caplog):
    caplog.set_level(logging.DEBUG)
    client, _ = make(FakeResponse(200, LOGIN), failure(401, "unauthorized"))
    client.session({"email": "asha@example.com"})
    with pytest.raises(PartnerError):
        client.session({"email": "asha@example.com"})
    assert caplog.records, "the client should log each call"
    assert KEY not in caplog.text
    assert "https://" not in caplog.text
    assert "asha@example.com" not in caplog.text


@pytest.mark.parametrize("failure", [
    requests.exceptions.InvalidHeader(f"Invalid header value {KEY!r}\r"),  # a key with \r (requests)
    ValueError(f"Invalid header value b'Bearer {KEY}\n'"),  # a trailing \n (http.client)
])
def test_unexpected_transport_failures_never_carry_the_key_out(failure, caplog):
    caplog.set_level(logging.DEBUG)
    client, _ = make(failure)
    with pytest.raises(PartnerError) as error:
        client.session({})
    assert (error.value.code, error.value.http_status) == ("partner_unavailable", 502)
    assert KEY not in str(error.value) and KEY not in caplog.text
    assert error.value.__cause__ is None and error.value.__suppress_context__


@pytest.mark.parametrize("status,code,message", [
    (403, {"nested": "x"}, "Blocked"),           # unhashable code
    (403, "https://evil.example/x", "Blocked"),  # a code that would be a URL in our events
    (409, "account_exists", 7),                  # a message that isn't text
])
def test_a_malformed_partner_error_is_still_a_clean_partner_error(status, code, message):
    client, _ = make(FakeResponse(status, {"success": False, "error": {"code": code, "message": message}}))
    with pytest.raises(PartnerError) as error:
        client.session({})
    assert isinstance(error.value.partner_code, str) and "://" not in error.value.partner_code
