"""Spec A §4: the HTTP contract of the email verification endpoints."""
from types import SimpleNamespace
from unittest import mock

import jwt
import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from api.email_verification import views
from api.email_verification.errors import VerificationError

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "email-views"}}
factory = APIRequestFactory()
USER = SimpleNamespace(id="u-1", email="asha@example.com", password="hash",
                       email_verified_at=None, email_verified_via=None)
SENT = {"expires_in": 600, "resend_after": 60, "sent_to": "a•••@example.com"}


@pytest.fixture(autouse=True)
def isolated_cache():
    with override_settings(CACHES=LOCMEM):
        cache.clear()
        yield
        cache.clear()


def bearer(user_id="u-1"):
    token = jwt.encode({"id": user_id, "expiry": "2099-01-01 00:00:00+0000", "roles": []},
                       settings.SECRET_KEY, algorithm="HS256")
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def call(view_cls, method="post", data=None, **headers):
    request = getattr(factory, method)("/x/", data or {}, format="json", **headers)
    return view_cls.as_view()(request)


def test_signup_code_success_uses_the_standard_envelope():
    with mock.patch.object(views.service, "send_signup_code", return_value=SENT) as send:
        response = call(views.SignupEmailCodeAPI, data={"email": "asha@example.com"})
    send.assert_called_once_with("asha@example.com")
    assert response.status_code == 200
    assert response.data["hasError"] is False
    assert response.data["response"] == SENT


def test_errors_carry_a_machine_readable_code():
    with mock.patch.object(views.service, "send_signup_code", side_effect=VerificationError("email_taken")):
        response = call(views.SignupEmailCodeAPI, data={"email": "asha@example.com"})
    assert response.status_code == 409
    assert response.data["statusCode"] == 409
    assert response.data["message"]["error_code"] == "email_taken"
    assert response.data["message"]["general"] == ["An account with this email already exists. Sign in instead."]


def test_cooldown_errors_include_retry_after():
    with mock.patch.object(views.service, "send_signup_code",
                           side_effect=VerificationError("code_cooldown", retry_after=42)):
        response = call(views.SignupEmailCodeAPI, data={"email": "asha@example.com"})
    assert response.status_code == 429
    assert response.data["response"] == {"retry_after": 42}


def test_a_throttled_request_answers_in_the_same_envelope():
    with mock.patch.object(views.EmailCodeIPThrottle, "allow_request", return_value=False), \
            mock.patch.object(views.EmailCodeIPThrottle, "wait", return_value=42.2):
        response = call(views.SignupEmailCodeAPI, data={"email": "asha@example.com"})
    assert response.status_code == 429
    assert response.data["message"]["error_code"] == "code_rate_limited"
    assert response.data["response"]["retry_after"] == 43


def test_verify_passes_email_and_code():
    with mock.patch.object(views.service, "verify_signup_code",
                           return_value={"email_verification_token": "t", "expires_in": 3600}) as verify:
        response = call(views.SignupEmailCodeVerifyAPI, data={"email": "asha@example.com", "code": "123456"})
    verify.assert_called_once_with("asha@example.com", "123456")
    assert response.data["response"]["email_verification_token"] == "t"


def test_account_endpoints_require_a_token():
    response = call(views.EmailVerificationStatusAPI, method="get")
    assert response.status_code == 403


def test_status_returns_the_current_user_state():
    with mock.patch.object(views, "_current_user", return_value=USER):
        response = call(views.EmailVerificationStatusAPI, method="get", **bearer())
    assert response.status_code == 200
    assert response.data["response"]["verified"] is False
    assert response.data["response"]["has_password"] is True
    # Spec C D2: there is no enforcement switch to report.
    assert "enforced" not in response.data["response"]


def test_a_vanished_user_gets_user_not_found():
    with mock.patch.object(views, "_current_user", return_value=None):
        response = call(views.VerifyEmailRequestAPI, **bearer())
    assert response.status_code == 404
    assert response.data["message"]["error_code"] == "user_not_found"


def test_change_request_passes_the_new_email_and_password():
    with mock.patch.object(views, "_current_user", return_value=USER), \
            mock.patch.object(views.service, "request_email_change", return_value=SENT) as request_change:
        response = call(views.ChangeEmailRequestAPI,
                        data={"new_email": "new@example.com", "current_password": "pw"}, **bearer())
    assert response.status_code == 200
    request_change.assert_called_once_with(USER, "new@example.com", "pw")


def test_change_confirm_passes_the_code():
    with mock.patch.object(views, "_current_user", return_value=USER), \
            mock.patch.object(views.service, "confirm_email_change",
                              return_value={"email": "new@example.com", "verified": True}) as confirm:
        response = call(views.ChangeEmailConfirmAPI, data={"code": "123456"}, **bearer())
    confirm.assert_called_once_with(USER, "123456")
    assert response.data["response"]["email"] == "new@example.com"
