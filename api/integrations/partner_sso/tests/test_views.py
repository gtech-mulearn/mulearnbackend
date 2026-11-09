"""Spec B §4: the HTTP contract, Cache-Control, and URL wiring."""
from types import SimpleNamespace
from unittest import mock

import jwt
import pytest
from django.conf import settings
from django.urls import Resolver404, resolve
from rest_framework.test import APIRequestFactory

from api.integrations.partner_sso import views
from api.integrations.partner_sso.errors import PartnerError

factory = APIRequestFactory()
USER = SimpleNamespace(id="u-1", full_name="Asha Nair")
ADAPTER = SimpleNamespace(display_name="Futuremug")


def bearer():
    token = jwt.encode({"id": "u-1", "expiry": "2099-01-01 00:00:00+0000", "roles": []},
                       settings.SECRET_KEY, algorithm="HS256")
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def call(view_cls, method, data=None, **headers):
    request = getattr(factory, method)("/x/", data or {}, format="json", **headers)
    with mock.patch.object(views.User.objects, "filter") as users:
        users.return_value.first.return_value = USER
        return view_cls.as_view(adapter=ADAPTER)(request, account_type="candidate")


def test_status_passes_through_and_is_never_cached():
    with mock.patch.object(views.service, "connection_status", return_value={"enabled": True}) as status:
        response = call(views.PartnerConnectionAPI, "get", **bearer())
    status.assert_called_once_with(ADAPTER, "candidate", USER)
    assert response.status_code == 200 and response.data["response"] == {"enabled": True}
    assert response["Cache-Control"] == "no-store"


def test_partner_errors_use_the_envelope_with_the_partner_name():
    with mock.patch.object(views.service, "sign_in", side_effect=PartnerError("partner_busy", retry_after=30)):
        response = call(views.PartnerSignInAPI, "post", **bearer())
    assert response.status_code == 429
    assert response.data["message"]["error_code"] == "partner_busy"
    assert response.data["message"]["general"] == ["Futuremug is busy right now. Try again in a minute."]
    assert response.data["response"] == {"retry_after": 30}
    assert response["Cache-Control"] == "no-store"


def test_authorize_passes_the_consent_fields():
    with mock.patch.object(views.service, "authorize", return_value={"status": "login"}) as authorize:
        call(views.PartnerAuthorizeAPI, "post", {"consent_version": "fm-2026-10-12", "accepted": True}, **bearer())
    kwargs = authorize.call_args.kwargs
    assert (kwargs["consent_version"], kwargs["accepted"]) == ("fm-2026-10-12", True)
    assert kwargs["request"] is not None


def test_delete_disconnects():
    with mock.patch.object(views.service, "disconnect", return_value={"status": "disconnected"}) as disconnect:
        response = call(views.PartnerConnectionAPI, "delete", **bearer())
    assert response.data["response"] == {"status": "disconnected"}
    disconnect.assert_called_once()


def test_a_token_is_required():
    assert call(views.PartnerConnectionAPI, "get").status_code == 403


@pytest.mark.parametrize("path,view", [
    ("/api/v1/integrations/futuremug/candidate/", "PartnerConnectionAPI"),
    ("/api/v1/integrations/futuremug/company/authorize/", "PartnerAuthorizeAPI"),
    ("/api/v1/integrations/futuremug/college/sign-in/", "PartnerSignInAPI"),
])
def test_routes_are_wired_to_the_futuremug_adapter(path, view):
    match = resolve(path)
    assert match.func.view_class.__name__ == view
    assert match.func.view_initkwargs["adapter"].provider == "futuremug"


def test_unknown_account_types_do_not_route():
    with pytest.raises(Resolver404):
        resolve("/api/v1/integrations/futuremug/admin/")
