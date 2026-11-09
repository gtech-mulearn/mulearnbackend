"""Spec A §3.5 (profile PATCH) and §3.6 (password reset proves the inbox)."""
from types import SimpleNamespace
from unittest import mock

import jwt
from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from api.dashboard.profile import profile_view
from api.dashboard.user import dash_user_views

factory = APIRequestFactory()
USER = SimpleNamespace(id="u-1", email="asha@example.com")


def bearer():
    token = jwt.encode({"id": "u-1", "expiry": "2099-01-01 00:00:00+0000", "roles": []},
                       settings.SECRET_KEY, algorithm="HS256")
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def patch_profile(body):
    with mock.patch.object(profile_view.UserProfileEditView, "_get_user", return_value=USER), \
            mock.patch.object(profile_view.profile_serializer, "UserProfileEditSerializer") as serializer_cls:
        serializer_cls.return_value.is_valid.return_value = False
        serializer_cls.return_value.errors = {}
        request = factory.patch("/api/v1/dashboard/profile/", body, format="json", **bearer())
        response = profile_view.UserProfileEditView.as_view()(request)
    return response, serializer_cls


def test_patch_refuses_an_email_change():
    response, serializer_cls = patch_profile({"email": "new@example.com"})
    assert response.status_code == 400
    assert response.data["message"]["error_code"] == "email_change_requires_verification"
    serializer_cls.assert_not_called()


def test_resending_the_same_email_in_another_case_is_not_a_change():
    _, serializer_cls = patch_profile({"email": "Asha@Example.com", "full_name": "Asha N"})
    serializer_cls.assert_called_once()


@override_settings(EMAIL_VERIFICATION_ENFORCED=False)
def test_patch_refuses_an_email_change_whatever_the_settings():
    # Spec C D2b: only the verified change flow changes an email.
    response, serializer_cls = patch_profile({"email": "new@example.com"})
    assert response.status_code == 400
    assert response.data["message"]["error_code"] == "email_change_requires_verification"
    serializer_cls.assert_not_called()


def reset_password(status, body):
    """save_password with authserver (which owns user.password) answering `status`."""
    forget_user = mock.Mock(user_id="u-1", user=mock.Mock(email="asha@example.com"))
    request = SimpleNamespace(data={"password": "new-password-1"})
    with mock.patch.object(dash_user_views.authserver_client, "call", return_value=(status, body)), \
            mock.patch.object(dash_user_views.authserver_client, "error_message", return_value="Too weak"), \
            mock.patch.object(dash_user_views, "mark_email_verified_if_current") as mark:
        response = dash_user_views.ResetPasswordConfirmAPI().save_password(request, forget_user)
    return response, mark, forget_user


def test_password_reset_records_proof_of_the_inbox():
    response, mark, forget_user = reset_password(200, {"sessions_revoked": True})
    assert response.status_code == 200
    mark.assert_called_once_with("u-1", "asha@example.com", "password_reset")
    forget_user.delete.assert_called_once_with()


def test_a_refused_password_records_no_proof_and_keeps_the_link():
    # The person retries with the same link; the proof comes with the reset
    # that actually completes.
    response, mark, forget_user = reset_password(400, {"message": {"general": ["Too weak"]}})
    assert response.data["hasError"] is True
    mark.assert_not_called()
    forget_user.delete.assert_not_called()
