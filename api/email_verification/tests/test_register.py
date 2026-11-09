"""Spec A §3.3: /register/ checks the signup token and records what it proved."""
from types import SimpleNamespace
from unittest import mock

from django.test import override_settings
from rest_framework.test import APIRequestFactory

from api.email_verification.tokens import make_signup_token
from api.register import register_views

factory = APIRequestFactory()
SIGNUP = {"full_name": "Asha Nair", "email": "Asha@Example.com", "password": "pw-123456", "role": "role-1"}


def post(body):
    request = factory.post("/api/v1/register/", body, format="json")
    return register_views.RegisterDataAPI.as_view()(request)


def created_user():
    return SimpleNamespace(id="u-1", email="asha@example.com", muid="asha@mulearn")


def patched():
    """Everything RegisterDataAPI touches beyond our logic."""
    return [
        mock.patch.object(register_views.serializers, "RegisterSerializer"),
        mock.patch.object(register_views.serializers, "UserDetailSerializer"),
        mock.patch.object(register_views, "get_auth_token", return_value={"accessToken": "a", "refreshToken": "r"}),
        mock.patch.object(register_views, "send_email"),
        mock.patch.object(register_views, "cache"),
        mock.patch.object(register_views, "mark_email_verified_if_current"),
    ]


def test_signup_without_a_token_is_refused_before_anything_is_created():
    with mock.patch.object(register_views.serializers, "RegisterSerializer") as serializer_cls:
        response = post({"user": SIGNUP})
    assert response.status_code == 400
    assert response.data["message"]["error_code"] == "email_verification_required"
    serializer_cls.assert_not_called()


def test_signup_with_a_matching_token_is_recorded_as_proof():
    managers = patched()
    serializer_cls, detail_cls, *_, mark = [m.start() for m in managers]
    try:
        serializer_cls.return_value.is_valid.return_value = True
        serializer_cls.return_value.save.return_value = created_user()
        detail_cls.return_value.data = {"muid": "asha@mulearn"}
        response = post({"user": SIGNUP, "email_verification_token": make_signup_token("asha@example.com")})
    finally:
        for manager in managers:
            manager.stop()
    assert response.status_code == 200
    # Stored lowercase, whatever was typed (spec A §3.1).
    assert serializer_cls.call_args.kwargs["data"]["user"]["email"] == "asha@example.com"
    mark.assert_called_once_with("u-1", "asha@example.com", "signup")


def test_a_non_object_user_is_refused_not_a_crash():
    # No email means nothing can be proven, so the verification check refuses
    # it before the serializer (spec C D2); what matters is no TypeError.
    with mock.patch.object(register_views.serializers, "RegisterSerializer") as serializer_cls:
        response = post({"user": "not-an-object"})
    assert response.status_code == 400
    assert response.data["message"]["error_code"] == "email_verification_required"
    serializer_cls.assert_not_called()


@override_settings(EMAIL_VERIFICATION_ENFORCED=False)
def test_signup_without_a_token_is_refused_whatever_the_settings():
    # Spec C D2: verification is unconditional; the old flag is not read.
    with mock.patch.object(register_views.serializers, "RegisterSerializer") as serializer_cls:
        response = post({"user": SIGNUP})
    assert response.status_code == 400
    assert response.data["message"]["error_code"] == "email_verification_required"
    serializer_cls.assert_not_called()


def test_google_reissue_records_the_address_google_proved():
    # The orphan lookup matches under the DB collation, so a look-alike row can
    # come back; the proof must be checked against what Google actually proved.
    existing = SimpleNamespace(id="u-9", email="ceo@exämple.com", password=None, suspended_at=None)
    google = {"email": "CEO@example.com", "fullName": "C E O", "email_verified": True}
    with mock.patch.object(register_views, "verify_google_temp_token", return_value=google), \
            mock.patch.object(register_views, "User") as user_model, \
            mock.patch.object(register_views, "get_auth_token_by_id", return_value={"accessToken": "a"}), \
            mock.patch.object(register_views.serializers, "UserDetailSerializer"), \
            mock.patch.object(register_views, "mark_email_verified_if_current") as mark:
        user_model.every.filter.return_value.first.return_value = existing
        response = post({"user": {"full_name": "C E O", "role": "role-1"}, "tempToken": "t"})
    assert response.status_code == 200
    mark.assert_called_once_with("u-9", "ceo@example.com", "google")
