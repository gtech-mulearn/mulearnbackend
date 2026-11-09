"""Spec A §3.3-§3.5: what each flow accepts, refuses and records."""
import contextlib
from types import SimpleNamespace
from unittest import mock

import pytest
from django.core.cache import cache
from django.db import IntegrityError
from django.test import override_settings

from api.email_verification import service, tokens
from api.email_verification.errors import VerificationError

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "email-service"}}


@pytest.fixture(autouse=True)
def isolated_cache():
    with override_settings(CACHES=LOCMEM):
        cache.clear()
        yield
        cache.clear()


@pytest.fixture
def mailbox():
    sent = []
    with mock.patch.object(service, "_send_code_mail", lambda purpose, email, code: sent.append((purpose, email, code))):
        yield sent


def make_user(**overrides):
    fields = {"id": "u-1", "email": "asha@example.com", "password": "pbkdf2_sha256$hash",
              "email_verified_at": None, "email_verified_via": None}
    fields.update(overrides)
    return SimpleNamespace(**fields)


def raises_code(code, func, *args, **kwargs):
    with pytest.raises(VerificationError) as error:
        func(*args, **kwargs)
    assert error.value.code == code
    return error.value


class TestSignup:
    def test_rejects_a_malformed_email(self, mailbox):
        raises_code("invalid_email", service.send_signup_code, "not-an-email")
        assert mailbox == []

    def test_rejects_a_registered_email(self, mailbox):
        with mock.patch.object(service, "_email_in_use", return_value=True):
            raises_code("email_taken", service.send_signup_code, "asha@example.com")
        assert mailbox == []

    def test_sends_to_the_normalised_address_and_masks_it(self, mailbox):
        with mock.patch.object(service, "_email_in_use", return_value=False):
            result = service.send_signup_code("  Asha@Example.com ")
        assert result == {"expires_in": 600, "resend_after": 60, "sent_to": "a•••@example.com"}
        assert mailbox[0][:2] == ("signup", "asha@example.com")

    def test_a_correct_code_yields_a_token_bound_to_the_email(self, mailbox):
        with mock.patch.object(service, "_email_in_use", return_value=False):
            service.send_signup_code("asha@example.com")
        result = service.verify_signup_code("Asha@Example.com", mailbox[0][2])
        assert result["expires_in"] == 3600
        assert tokens.signup_token_matches(result["email_verification_token"], "asha@example.com")


class TestResolveSignupVerification:
    def resolve(self, **overrides):
        args = {"email": "asha@example.com", "token": None, "is_google_signup": False,
                "google_email_verified": False}
        args.update(overrides)
        return service.resolve_signup_verification(**args)

    def test_google_counts_only_with_the_verified_claim(self):
        assert self.resolve(is_google_signup=True, google_email_verified=True) == "google"
        # Spec C D2a: an unverified provider address proves nothing, with no code fallback.
        raises_code("email_verification_required", self.resolve,
                    is_google_signup=True, google_email_verified=False)

    def test_mixed_case_email_still_matches_its_token(self):
        token = tokens.make_signup_token("asha@example.com")
        assert self.resolve(email="Asha@Example.com", token=token) == "signup"

    def test_no_or_foreign_token_is_always_refused(self):
        raises_code("email_verification_required", self.resolve, token=None)
        other = tokens.make_signup_token("someone@example.com")
        raises_code("email_verification_required", self.resolve, token=other)


class TestAccountVerification:
    def test_already_verified_sends_nothing(self, mailbox):
        user = make_user(email_verified_at="2026-10-01T00:00:00Z")
        assert service.request_account_code(user) == {"already_verified": True}
        assert mailbox == []

    def test_confirm_records_account_proof(self, mailbox):
        user = make_user()
        service.request_account_code(user)
        with mock.patch.object(service, "mark_email_verified_if_current", return_value=True) as mark, \
                mock.patch.object(service, "_verified_at", return_value="2026-10-12T10:00:00Z"):
            result = service.confirm_account_code(user, mailbox[0][2])
        mark.assert_called_once_with("u-1", "asha@example.com", "account")
        assert result == {"verified": True, "verified_at": "2026-10-12T10:00:00Z"}

    def test_a_code_proves_nothing_after_the_email_changed(self, mailbox):
        user = make_user()
        service.request_account_code(user)
        with mock.patch.object(service, "mark_email_verified_if_current", return_value=False), \
                mock.patch.object(service, "_verified_at", return_value=None):
            raises_code("code_expired", service.confirm_account_code, user, mailbox[0][2])


class TestEmailChange:
    def test_the_same_address_is_refused(self, mailbox):
        raises_code("email_unchanged", service.request_email_change, make_user(), "ASHA@example.com", "pw")

    def test_password_accounts_must_re_enter_their_password(self, mailbox):
        raises_code("password_required", service.request_email_change, make_user(), "new@example.com", None)
        with mock.patch.object(service, "check_password", return_value=False):
            raises_code("invalid_password", service.request_email_change, make_user(), "new@example.com", "nope")
        assert mailbox == []

    def test_passwordless_accounts_skip_the_password(self, mailbox):
        with mock.patch.object(service, "_email_in_use", return_value=False):
            result = service.request_email_change(make_user(password=None), "new@example.com")
        assert result["sent_to"] == "n•••@example.com"

    def test_a_taken_address_is_refused(self, mailbox):
        with mock.patch.object(service, "check_password", return_value=True), \
                mock.patch.object(service, "_email_in_use", return_value=True):
            raises_code("email_taken", service.request_email_change, make_user(), "new@example.com", "pw")

    def test_the_code_goes_to_the_new_address(self, mailbox):
        with mock.patch.object(service, "check_password", return_value=True), \
                mock.patch.object(service, "_email_in_use", return_value=False):
            service.request_email_change(make_user(), "New@Example.com", "pw")
        assert mailbox[0][:2] == ("change", "new@example.com")

    def test_confirm_applies_the_change(self, mailbox):
        user = make_user(password=None)
        with mock.patch.object(service, "_email_in_use", return_value=False):
            service.request_email_change(user, "new@example.com")
        with mock.patch.object(service, "_apply_email_change") as apply:
            result = service.confirm_email_change(user, mailbox[0][2])
        apply.assert_called_once_with("u-1", "new@example.com")
        assert result == {"email": "new@example.com", "verified": True}

    def test_address_taken_while_pending_is_reported_not_crashed(self, mailbox):
        user = make_user(password=None)
        with mock.patch.object(service, "_email_in_use", return_value=False):
            service.request_email_change(user, "new@example.com")
        locked = mock.Mock()
        locked.save.side_effect = IntegrityError("Duplicate entry for key 'email'")
        with mock.patch.object(service.transaction, "atomic", contextlib.nullcontext), \
                mock.patch.object(service, "_email_in_use", return_value=False), \
                mock.patch.object(service, "User") as user_model:
            user_model.every.select_for_update.return_value.get.return_value = locked
            raises_code("email_taken", service.confirm_email_change, user, mailbox[0][2])
        locked.mark_email_verified_on_save.assert_called_once_with("email_change")


class TestProofHelper:
    """§3.6: proof fills a NULL, and only for the exact current address."""

    def locked_row(self, user_model, row):
        user_model.every.select_for_update.return_value.filter.return_value.values.return_value.first.return_value = row
        user_model.every.filter.return_value.update.return_value = 1

    def test_proof_is_not_credited_to_a_look_alike_address(self):
        # MySQL's accent-insensitive collation treats these as equal in SQL.
        with mock.patch.object(service.transaction, "atomic", contextlib.nullcontext), \
                mock.patch.object(service, "User") as user_model:
            self.locked_row(user_model, {"email": "ceo@example.com", "email_verified_at": None})
            assert service.mark_email_verified_if_current("u-1", "ceo@exämple.com", "account") is False
        user_model.every.filter.return_value.update.assert_not_called()

    def test_proof_fills_a_null_for_the_current_address(self):
        with mock.patch.object(service.transaction, "atomic", contextlib.nullcontext), \
                mock.patch.object(service, "User") as user_model:
            self.locked_row(user_model, {"email": "Asha@Example.com", "email_verified_at": None})
            assert service.mark_email_verified_if_current("u-1", "asha@example.com", "signup") is True
        update = user_model.every.filter.return_value.update
        update.assert_called_once()
        assert update.call_args.kwargs["email_verified_via"] == "signup"

    def test_existing_proof_is_never_overwritten(self):
        with mock.patch.object(service.transaction, "atomic", contextlib.nullcontext), \
                mock.patch.object(service, "User") as user_model:
            self.locked_row(user_model, {"email": "asha@example.com", "email_verified_at": "2026-01-01T00:00:00Z"})
            assert service.mark_email_verified_if_current("u-1", "asha@example.com", "signup") is False
        user_model.every.filter.return_value.update.assert_not_called()
