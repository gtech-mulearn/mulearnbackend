"""
verified_role_required: the token must carry the role AND the database must hold
a verified, active, unrevoked, global link for it. Signup accepts any role and
tokens carry unverified ones, so the token alone is not proof.
"""
from unittest import mock

import jwt
import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from api.dashboard.auth_admin import auth_admin_views
from utils import permission
from utils.permission import CustomizePermission, verified_role_required
from utils.response import CustomResponse

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "verified-role"}}
factory = APIRequestFactory()


@pytest.fixture(autouse=True)
def _memory_cache():
    with override_settings(CACHES=LOCMEM):
        cache.clear()
        yield


class Guarded(APIView):
    authentication_classes = [CustomizePermission]

    @verified_role_required(["Admins"])
    def get(self, request):
        return CustomResponse(response={"ok": True}).get_success_response()


def bearer(roles):
    token = jwt.encode({"id": "u-1", "expiry": "2099-01-01 00:00:00+0000", "roles": list(roles)},
                       settings.SECRET_KEY, algorithm="HS256")
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def call(roles):
    return Guarded.as_view()(factory.get("/x/", **bearer(roles)))


def test_a_verified_admin_gets_through():
    with mock.patch.object(permission, "holds_verified_role", return_value=True) as check:
        response = call(["Admins"])
    assert response.data["response"] == {"ok": True}
    check.assert_called_once_with("u-1", ["Admins"])


def test_an_admin_role_only_in_the_token_is_refused():
    with mock.patch.object(permission, "holds_verified_role", return_value=False):
        response = call(["Admins"])
    assert response.data["hasError"] is True
    assert response.data["message"]["general"] == ["You do not have the required role to access this page."]


def test_a_token_without_the_role_never_reaches_the_database():
    with mock.patch.object(permission, "holds_verified_role") as check:
        response = call(["Student"])
    assert response.data["hasError"] is True
    check.assert_not_called()


def test_the_database_check_wants_a_verified_live_global_link():
    with mock.patch.object(permission.UserRoleLink, "objects") as links:
        links.filter.return_value.exists.return_value = True
        assert permission.holds_verified_role("u-1", ["Admins"]) is True
    links.filter.assert_called_once_with(
        user_id="u-1", role__title__in=["Admins"], ig__isnull=True,
        verified=True, is_active=True, revoked_at__isnull=True,
    )


@pytest.mark.parametrize("view, method, path", [
    (auth_admin_views.ClientListAPI, "get", "/clients/"),
    (auth_admin_views.ClientListAPI, "post", "/clients/"),
    (auth_admin_views.SigninPolicyAPI, "put", "/signin-policy/"),
    (auth_admin_views.SessionRevokeAPI, "post", "/sessions/revoke/"),
])
def test_the_sign_in_admin_console_needs_a_verified_admin(view, method, path):
    with mock.patch.object(permission, "holds_verified_role", return_value=False), \
         mock.patch.object(auth_admin_views, "_proxy") as proxy:
        response = view.as_view()(getattr(factory, method)(path, {}, format="json", **bearer(["Admins"])))
    assert response.data["hasError"] is True
    proxy.assert_not_called()
