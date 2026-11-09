"""Spec B §3.4: the sign-in sequence and everything it must refuse."""
from types import SimpleNamespace
from unittest import mock

import pytest

from api.integrations.partner_sso import ratelimit, service
from api.integrations.partner_sso.adapter import (
    Contact, ContactChange, ContactSnapshot, PartnerAccountNotFound, PreviewRow, SessionResult,
)
from api.integrations.partner_sso.consent import ConsentDocument
from api.integrations.partner_sso.errors import PartnerError
from api.integrations.partner_sso.subjects import Resolution, SubjectKind

USER = SimpleNamespace(id="u-1", full_name="Asha Nair", email="asha@example.com", email_verified_at="2026-10-12")
MANAGER = Resolution(SubjectKind.LEARNER, subject_type="user", subject_id="u-1",
                     subject_name="Asha Nair", manager=USER, can_manage=True)
LOGIN = SessionResult(status="login", login_url="https://partner.example/sso/login/abc",
                      expires_in=120, account_created=True)


class FakeAdapter:
    provider = "fake"
    display_name = "Partner"
    account_types = {"candidate": SubjectKind.LEARNER}

    def __init__(self):
        self.calls = []
        self.enabled = True
        self.email = "asha@example.com"
        self.session_result = LOGIN
        self.update_error = None

    def is_enabled(self):
        return self.enabled

    def rate_per_minute(self):
        return 55

    def consent_version(self):
        return "v1"

    def consent_document(self, account_type):
        return ConsentDocument(version="v1", title="Connect Partner", subtitle="s", purpose="p", sections=(),
                               notes=(), checkbox_label="{terms} {privacy}", terms_url="https://t", privacy_url="https://p")

    def build_contact(self, account_type, resolution):
        return Contact(email=self.email, first_name="Asha", last_name="Nair", phone="9876543210",
                       organization_name=None, preview=(PreviewRow("Email", self.email),))

    def update_contact(self, account_type, current_email, change):
        self.calls.append(("update_contact", current_email, change))
        if self.update_error:
            raise self.update_error
        return ContactSnapshot(email=change.new_email or current_email, first_name=change.new_first_name,
                               last_name=change.new_last_name, phone=change.new_phone)

    def open_session(self, account_type, contact):
        self.calls.append(("session", contact.email))
        if isinstance(self.session_result, Exception):
            raise self.session_result
        return self.session_result


class FakeLink(SimpleNamespace):
    def save(self, **kwargs):
        self.saves = getattr(self, "saves", 0) + 1


def make_link(**overrides):
    fields = {
        "id": "l-1", "provider": "fake", "account_type": "candidate", "subject_type": "user", "subject_id": "u-1",
        "contact_user_id": "u-1", "contact_user": USER, "status": "active", "external_email": "asha@example.com",
        "synced_first_name": "Asha", "synced_last_name": "Nair", "synced_phone": "9876543210",
        "consent_version": "v1", "consented_at": None, "consented_by_id": "u-1",
        "disconnected_at": None, "disconnected_by_id": None, "last_login_at": None,
        "last_synced_at": None, "last_error_code": None,
    }
    fields.update(overrides)
    return FakeLink(**fields)


@pytest.fixture
def env():
    adapter = FakeAdapter()
    state = SimpleNamespace(link=None, conflict=None, created=[])

    def new_link(adapter_, account_type, resolution):
        link = make_link(status="consented", external_email=None, synced_first_name=None, synced_last_name=None,
                         synced_phone=None, consent_version=None, consented_by_id=None,
                         contact_user_id=None, contact_user=None)
        state.created.append(link)
        state.link = link  # saved by authorize, so later reads find it
        return link

    with mock.patch.object(service, "resolve", return_value=MANAGER) as resolve, \
            mock.patch.object(service, "_get_link", side_effect=lambda a, r: state.link), \
            mock.patch.object(service, "_new_link", side_effect=new_link), \
            mock.patch.object(service, "_conflicting_link", side_effect=lambda a, link, email: state.conflict), \
            mock.patch.object(service, "is_email_verified", return_value=True) as verified, \
            mock.patch.object(service.events, "record_event") as record:
        yield SimpleNamespace(adapter=adapter, state=state, resolve=resolve, verified=verified, record=record)


def event_names(env):
    return [call.args[1] for call in env.record.call_args_list]


def raises_code(code, func, *args, **kwargs):
    with pytest.raises(PartnerError) as error:
        func(*args, **kwargs)
    assert error.value.code == code
    return error.value


class TestAuthorize:
    def test_records_consent_then_signs_in(self, env):
        result = service.authorize(env.adapter, "candidate", USER, consent_version="v1", accepted=True)
        assert result == {"status": "login", "login_url": LOGIN.login_url, "expires_in": 120, "account_created": True}
        link = env.state.created[0]
        assert (link.status, link.consented_by_id, link.consent_version, link.contact_user_id, link.external_email) == \
            ("active", "u-1", "v1", "u-1", "asha@example.com")
        assert event_names(env) == ["consent_granted", "login_issued"]
        assert env.record.call_args_list[0].kwargs["details"] == {"fields": ["email", "first_name", "last_name", "phone"]}
        assert env.adapter.calls == [("session", "asha@example.com")]

    def test_refuses_stale_terms(self, env):
        raises_code("consent_version_mismatch", service.authorize, env.adapter, "candidate", USER,
                    consent_version="v0", accepted=True)
        assert env.state.created == [] and env.record.call_count == 0

    def test_unverified_email_is_sent_to_verify_first(self, env):
        env.verified.return_value = False
        raises_code("email_unverified", service.authorize, env.adapter, "candidate", USER,
                    consent_version="v1", accepted=True)
        assert env.adapter.calls == []

    def test_non_managers_get_the_reason(self, env):
        env.resolve.return_value = Resolution(SubjectKind.LEARNER, reason="not_learner")
        error = raises_code("not_eligible", service.authorize, env.adapter, "candidate", USER,
                            consent_version="v1", accepted=True)
        assert error.reason == "not_learner"


class TestSignIn:
    def test_needs_this_persons_own_consent(self, env):
        env.state.link = make_link(consented_by_id="u-9")
        raises_code("consent_required", service.sign_in, env.adapter, "candidate", USER)

    def test_an_email_change_is_pushed_before_the_session(self, env):
        env.state.link = make_link(external_email="old@example.com")
        service.sign_in(env.adapter, "candidate", USER)
        assert env.adapter.calls == [
            ("update_contact", "old@example.com", ContactChange(new_email="asha@example.com")),
            ("session", "asha@example.com"),
        ]
        assert event_names(env) == ["contact_synced", "login_issued"]

    def test_a_retryable_failure_stops_before_the_session(self, env):
        env.state.link = make_link(external_email="old@example.com")
        env.adapter.update_error = PartnerError("partner_unavailable", partner_code="server_error", retryable=True)
        raises_code("partner_unavailable", service.sign_in, env.adapter, "candidate", USER)
        assert [call[0] for call in env.adapter.calls] == ["update_contact"]
        assert env.state.link.last_error_code == "server_error"
        assert event_names(env) == ["error"]

    def test_an_account_we_did_not_create_falls_through_to_the_session(self, env):
        env.state.link = make_link(external_email="old@example.com")
        env.adapter.update_error = PartnerAccountNotFound()
        service.sign_in(env.adapter, "candidate", USER)
        assert [call[0] for call in env.adapter.calls] == ["update_contact", "session"]
        assert env.state.link.external_email == "asha@example.com"

    def test_takeover_replaces_the_contact(self, env):
        env.state.link = make_link(contact_user_id="u-9", consented_by_id="u-1")
        service.sign_in(env.adapter, "candidate", USER)
        change = env.adapter.calls[0][2]
        assert change.replace_contact and change.new_email == "asha@example.com" and change.new_first_name == "Asha"
        replaced = env.record.call_args_list[0]
        assert replaced.args[1] == "contact_replaced"
        assert replaced.kwargs["details"]["previous_contact_user_id"] == "u-9"
        assert env.state.link.contact_user_id == "u-1"

    def test_pending_approval_is_recorded(self, env):
        env.state.link = make_link()
        env.adapter.session_result = SessionResult(status="pending_approval", pending_url="https://partner.example/pending",
                                                   message="Awaiting approval", account_created=True)
        result = service.sign_in(env.adapter, "candidate", USER)
        assert result["status"] == "pending_approval" and result["pending_url"].startswith("https://")
        assert env.state.link.status == "pending_approval"
        assert event_names(env) == ["pending_approval"]

    def test_a_rejected_account_is_remembered(self, env):
        env.state.link = make_link()
        env.adapter.session_result = PartnerError("partner_account_blocked", partner_code="account_rejected")
        raises_code("partner_account_blocked", service.sign_in, env.adapter, "candidate", USER)
        assert env.state.link.status == "rejected"

    def test_a_conflict_with_a_disconnected_link_calls_nothing(self, env):
        env.state.link = make_link()
        env.state.conflict = make_link(id="l-2", subject_id="u-7", status="disconnected")
        raises_code("email_in_use_by_other_link", service.sign_in, env.adapter, "candidate", USER)
        assert env.adapter.calls == []

    def test_a_conflict_moves_the_other_account_first(self, env):
        owner = SimpleNamespace(id="u-7", email="new.owner@example.com", email_verified_at="2026-10-01")
        env.state.link = make_link(external_email=None)
        env.state.conflict = make_link(id="l-2", subject_id="u-7", contact_user_id="u-7", contact_user=owner)
        service.sign_in(env.adapter, "candidate", USER)
        assert env.adapter.calls == [
            ("update_contact", "asha@example.com", ContactChange(new_email="new.owner@example.com")),
            ("session", "asha@example.com"),
        ]
        assert env.state.conflict.external_email == "new.owner@example.com"

    def test_the_same_person_in_two_roles_is_refused(self, env):
        env.state.link = make_link(external_email=None)
        env.state.conflict = make_link(id="l-2", subject_type="organization", subject_id="o-1")
        raises_code("email_in_use_by_other_link", service.sign_in, env.adapter, "candidate", USER)

    def test_concurrent_sign_ins_are_refused(self, env):
        env.state.link = make_link()
        with ratelimit.link_lock("fake", "user:u-1"):
            raises_code("in_progress", service.sign_in, env.adapter, "candidate", USER)

    def test_the_shared_budget_is_respected(self, env):
        env.state.link = make_link()
        with mock.patch.object(service.ratelimit, "take_partner_call", return_value=30):
            error = raises_code("partner_busy", service.sign_in, env.adapter, "candidate", USER)
        assert error.retry_after == 30 and env.adapter.calls == []


class TestDisconnect:
    def test_keeps_only_the_partner_email_and_needs_no_verified_email(self, env):
        env.verified.return_value = False
        env.state.link = make_link()
        assert service.disconnect(env.adapter, "candidate", USER) == {"status": "disconnected"}
        link = env.state.link
        assert (link.status, link.consent_version, link.consented_by_id, link.synced_phone) == ("disconnected", None, None, None)
        assert link.external_email == "asha@example.com"
        assert event_names(env) == ["disconnected"]


class TestStatus:
    def test_a_manager_sees_consent_preview_and_document(self, env):
        env.state.link = make_link(consented_by_id="u-9")
        status = service.connection_status(env.adapter, "candidate", USER)
        assert status["consent"]["needs_consent"] is True
        assert status["shared_data_preview"] == [{"label": "Email", "value": "asha@example.com", "note": None}]
        assert status["consent"]["document"]["title"] == "Connect Partner"
        assert status["connection"]["takeover_required"] is False
        assert status["connection"]["contact_name"] == "Asha Nair"

    def test_an_unusable_email_becomes_the_eligibility_reason(self, env):
        env.adapter.build_contact = mock.Mock(side_effect=PartnerError("email_not_supported", message="Too long"))
        eligibility = service.connection_status(env.adapter, "candidate", USER)["eligibility"]
        assert eligibility == {"eligible": False, "reason": "email_not_supported", "message": "Too long"}

    def test_a_disabled_integration_says_only_that(self, env):
        env.adapter.enabled = False
        assert service.connection_status(env.adapter, "candidate", USER) == {"enabled": False, "account_type": "candidate"}


class TestConcurrency:
    """Spec B §3.7 and §7: one actor per link at a time, and a withdrawal is never undone."""

    def test_a_disconnect_waits_for_a_running_sign_in(self, env):
        env.state.link = make_link()
        with ratelimit.link_lock("fake", "user:u-1"):
            raises_code("in_progress", service.disconnect, env.adapter, "candidate", USER)
        assert env.state.link.status == "active" and event_names(env) == []

    def test_a_link_disconnected_after_it_was_read_is_not_signed_in(self, env):
        stale = make_link()
        disconnected = make_link(status="disconnected", consent_version=None, consented_by_id=None)
        with mock.patch.object(service, "_get_link", side_effect=[stale, disconnected]):
            raises_code("consent_required", service.sign_in, env.adapter, "candidate", USER)
        assert env.adapter.calls == []
        assert not getattr(stale, "saves", 0)  # nothing written back over the withdrawal

    def test_another_subjects_link_is_moved_only_under_its_own_lock(self, env):
        owner = SimpleNamespace(id="u-7", email="new.owner@example.com", email_verified_at="2026-10-01")
        env.state.link = make_link(external_email=None)
        env.state.conflict = make_link(id="l-2", subject_id="u-7", contact_user_id="u-7", contact_user=owner)
        with ratelimit.link_lock("fake", "user:u-7"):
            raises_code("in_progress", service.sign_in, env.adapter, "candidate", USER)
        assert env.adapter.calls == []

    def test_the_lock_outlives_the_slowest_partner_calls(self, env):
        env.state.link = make_link()
        seen = []
        real_lock = ratelimit.link_lock

        def recording_lock(provider, key, timeout=30):
            seen.append(timeout)
            return real_lock(provider, key, timeout=timeout)

        with mock.patch.object(service.ratelimit, "link_lock", recording_lock):
            service.sign_in(env.adapter, "candidate", USER)
        # Up to three partner calls, each up to two (3 s + 10 s) attempts: about 80 s.
        assert seen and min(seen) >= 90
