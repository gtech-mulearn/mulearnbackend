"""Spec C §4.4: the protected identity endpoints authserver calls for express signup."""
from types import SimpleNamespace
from unittest import mock

import pytest
from django.core import signing
from django.urls import resolve
from rest_framework.test import APIRequestFactory

from api.email_verification import tokens
from api.email_verification.errors import VerificationError
from api.email_verification.tokens import make_signup_token
from api.protected.identity import views

factory = APIRequestFactory()
SENT = {"expires_in": 600, "resend_after": 60, "sent_to": "a•••@example.com"}


def call(view, body, key_ok=True):
    request = factory.post("/api/v1/protected/identity/", body, format="json", HTTP_PROTECTIONKEY="k")
    with mock.patch.object(views, "_key_is_valid", return_value=key_ok):
        return view.as_view()(request)


def test_signup_code_needs_the_protection_key():
    with mock.patch.object(views.service, "send_signup_code") as send:
        response = call(views.SignupCodeAPI, {"email": "a@example.com"}, key_ok=False)
    assert response.status_code == 400
    assert response.data["message"]["general"] == ["Invalid Key"]
    send.assert_not_called()


def test_signup_code_sends_through_spec_a():
    with mock.patch.object(views.service, "send_signup_code", return_value=SENT) as send:
        response = call(views.SignupCodeAPI, {"email": "Asha@Example.com"})
    assert response.status_code == 200
    assert response.data["response"] == SENT
    # The raw value: spec A normalises it.
    send.assert_called_once_with("Asha@Example.com")


def test_code_errors_use_the_spec_a_envelope():
    refusal = VerificationError("code_cooldown", retry_after=42)
    with mock.patch.object(views.service, "send_signup_code", side_effect=refusal):
        response = call(views.SignupCodeAPI, {"email": "a@example.com"})
    assert response.status_code == 429
    assert response.data["message"]["error_code"] == "code_cooldown"
    assert response.data["response"]["retry_after"] == 42


def test_verify_returns_the_signup_token():
    verified = {"email_verification_token": "t", "expires_in": 3600}
    with mock.patch.object(views.service, "verify_signup_code", return_value=verified) as verify:
        response = call(views.SignupCodeVerifyAPI, {"email": "a@example.com", "code": "123456"})
    assert response.status_code == 200
    assert response.data["response"]["email_verification_token"] == "t"
    verify.assert_called_once_with("a@example.com", "123456")


@pytest.mark.parametrize("name", ["SignupCodeAPI", "SignupCodeVerifyAPI"])
def test_protected_code_views_are_not_ip_throttled(name):
    # Every call comes from authserver's address; it limits per client IP itself.
    assert getattr(getattr(views, name), "throttle_scope", None) is None


@pytest.mark.parametrize("path, name", [
    ("/api/v1/protected/identity/signup-code/", "SignupCodeAPI"),
    ("/api/v1/protected/identity/signup-code/verify/", "SignupCodeVerifyAPI"),
])
def test_code_endpoints_are_routed(path, name):
    assert resolve(path).func.view_class is getattr(views, name)


# ── provision-member: no account without a proven inbox (spec C D2, D2a) ──

MEMBER = {"full_name": "Asha Nair", "email": "Asha@Example.com"}


def provision(body, mark_returns=True):
    """POST provision-member with a valid key and everything past our rule mocked."""
    created = SimpleNamespace(id="u-1", muid="asha@mulearn", email="asha@example.com")
    with mock.patch.object(views, "_key_is_valid", return_value=True), \
            mock.patch.object(views, "User") as user_model, \
            mock.patch.object(views, "UserSerializer") as serializer_cls, \
            mock.patch.object(views, "UserDetailSerializer"), \
            mock.patch.object(views, "send_email") as send_email, \
            mock.patch.object(views, "mark_email_verified_if_current", return_value=mark_returns) as mark:
        user_model.every.filter.return_value.exists.return_value = False
        serializer_cls.return_value.is_valid.return_value = True
        serializer_cls.return_value.save.return_value = created
        request = factory.post("/api/v1/protected/identity/provision-member/", body, format="json")
        response = views.ProvisionMemberAPI.as_view()(request)
    return response, serializer_cls, mark, send_email


def assert_refused(response, serializer_cls):
    assert response.status_code == 400
    assert response.data["message"]["error_code"] == "email_verification_required"
    assert response.data["response"] == {"email_verification_required": True}
    serializer_cls.assert_not_called()


def test_provision_without_proof_is_refused_before_anything_is_created():
    response, serializer_cls, mark, _ = provision(MEMBER)
    assert_refused(response, serializer_cls)
    mark.assert_not_called()


def test_provision_with_a_token_for_another_email_is_refused():
    response, serializer_cls, *_ = provision(
        {**MEMBER, "email_verification_token": make_signup_token("other@example.com")}
    )
    assert_refused(response, serializer_cls)


def test_look_alike_token_is_refused():
    # The DB collation folds accents; the proof must not.
    response, serializer_cls, *_ = provision({
        "full_name": "C E O", "email": "ceo@example.com",
        "email_verification_token": make_signup_token("ceo@exämple.com"),
    })
    assert_refused(response, serializer_cls)


def test_expired_token_is_refused():
    token = make_signup_token("asha@example.com")
    with mock.patch.object(tokens.signing, "loads", side_effect=signing.SignatureExpired("old")):
        response, serializer_cls, *_ = provision({**MEMBER, "email_verification_token": token})
    assert_refused(response, serializer_cls)


def test_unknown_provider_is_refused():
    response, serializer_cls, *_ = provision({**MEMBER, "email_verified_via": "facebook"})
    assert_refused(response, serializer_cls)


def test_token_proof_creates_a_verified_member():
    response, _, mark, _ = provision(
        {**MEMBER, "email_verification_token": make_signup_token("asha@example.com")}
    )
    assert response.status_code == 200
    mark.assert_called_once_with("u-1", "asha@example.com", "signup")


@pytest.mark.parametrize("via", ["google", "apple"])
def test_provider_proof_is_recorded(via):
    response, _, mark, _ = provision({**MEMBER, "email_verified_via": via})
    assert response.status_code == 200
    mark.assert_called_once_with("u-1", "asha@example.com", via)


def test_an_unrecorded_proof_rolls_the_account_back():
    response, _, _, send_email = provision({**MEMBER, "email_verified_via": "google"}, mark_returns=False)
    assert response.data["hasError"] is True
    assert response.data["message"]["general"] == ["Could not create the account"]
    send_email.delay.assert_not_called()
