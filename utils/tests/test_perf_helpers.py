"""
Unit tests for the shared helpers changed in the performance pass
(docs/perf/plan.md). None of them touch the database, so they run without the
test-database setup the endpoint suites need.

    DJANGO_SETTINGS_MODULE=mulearnbackend.settings pytest utils/tests/test_perf_helpers.py
"""
from datetime import datetime, timedelta, timezone
from unittest import mock

import jwt
import pytest
import requests
from django.conf import settings
from django.test import RequestFactory, override_settings
from rest_framework.request import Request

from utils import permission
from utils.permission import JWTUtils, RoleRequired
from utils.types import RoleType
from utils.utils import CommonUtils, external_json_request

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


def _token(**extra):
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S%z")
    payload = {"id": "u-1", "muid": "u1@mulearn", "roles": ["Student"], "expiry": expiry, **extra}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _get(query="", token=None):
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return Request(RequestFactory().get(f"/x{query}", **headers))


# ── CommonUtils.get_paginated_queryset with a list ─────────────────────────

ROWS = [{"name": f"Row {i:02d}", "count": i % 3, "nested": {"city": "Kochi" if i % 2 else "Delhi"}}
        for i in range(25)]


def test_list_pagination_matches_queryset_shape():
    result = CommonUtils.get_paginated_queryset(list(ROWS), _get("?pageIndex=2&perPage=10"), ["name"])
    assert [row["name"] for row in result["queryset"]] == [f"Row {i:02d}" for i in range(10, 20)]
    assert result["pagination"] == {
        "count": 25, "totalPages": 3, "isNext": True, "isPrev": True, "nextPage": 3,
    }


def test_list_pagination_out_of_range_page_returns_last_page():
    result = CommonUtils.get_paginated_queryset(list(ROWS), _get("?pageIndex=99&perPage=10"), [])
    assert [row["name"] for row in result["queryset"]] == [f"Row {i:02d}" for i in range(20, 25)]
    assert result["pagination"]["isNext"] is False


def test_list_pagination_caps_per_page():
    result = CommonUtils.get_paginated_queryset(list(ROWS) * 50, _get("?perPage=999999"), [])
    assert len(result["queryset"]) == 1000


def test_list_search_is_case_insensitive_and_follows_lookups():
    result = CommonUtils.get_paginated_queryset(
        list(ROWS), _get("?search=kOcHi&perPage=100"), ["name", "nested__city"]
    )
    assert result["pagination"]["count"] == 12  # the odd rows


def test_list_sort_uses_sort_fields_mapping():
    result = CommonUtils.get_paginated_queryset(
        list(ROWS), _get("?sortBy=-count&perPage=100"), [], {"count": "count"}
    )
    counts = [row["count"] for row in result["queryset"]]
    assert counts == sorted(counts, reverse=True)


def test_list_without_pagination_returns_list():
    assert CommonUtils.get_paginated_queryset(list(ROWS), _get(), [], is_pagination=False) == ROWS


# ── JWT is decoded once per request ────────────────────────────────────────

def test_jwt_payload_decoded_once_per_request():
    request = _get(token=_token())
    real_decode = jwt.decode
    with mock.patch.object(permission.jwt, "decode", side_effect=real_decode) as decode:
        JWTUtils.is_jwt_authenticated(request)
        assert JWTUtils.fetch_user_id(request) == "u-1"
        assert JWTUtils.fetch_muid(request) == "u1@mulearn"
        assert JWTUtils.fetch_role(request) == ["Student"]
        # The plain HttpRequest behind the DRF Request shares the cache.
        assert JWTUtils.fetch_user_id(request._request) == "u-1"
    assert decode.call_count == 1


def test_jwt_cache_is_keyed_on_header():
    request = _get(token=_token())
    assert JWTUtils.fetch_user_id(request) == "u-1"
    request._request.META["HTTP_AUTHORIZATION"] = f"Bearer {_token(id='u-2')}"
    assert JWTUtils.fetch_user_id(request) == "u-2"


def test_invalid_signature_still_rejected():
    bad = jwt.encode({"id": "x", "expiry": "2999-01-01 00:00:00+0000"}, "wrong-key", algorithm="HS256")
    with pytest.raises(permission.UnauthorizedAccessException):
        JWTUtils.is_jwt_authenticated(_get(token=bad))


# ── RoleRequired resolves enums once and still checks roles ────────────────

def test_role_required_accepts_enum_and_value():
    decorator = RoleRequired([RoleType.ADMIN, RoleType.STUDENT.value])
    assert decorator.roles == [RoleType.ADMIN.value, RoleType.STUDENT.value]

    view = decorator(lambda obj, request: "allowed")
    assert view(None, _get(token=_token(roles=["Student"]))) == "allowed"
    denied = view(None, _get(token=_token(roles=["Mentor"])))
    assert denied.data["hasError"] is True


# ── dynamic_role_required access lists are cached ─────────────────────────

@override_settings(CACHES=LOCMEM)
def test_dynamic_access_is_cached_and_invalidated():
    roles_qs = mock.MagicMock()
    roles_qs.values_list.return_value = ["Admins"]
    users_qs = mock.MagicMock()
    users_qs.values_list.return_value = ["u-9"]
    with mock.patch.object(permission.DynamicRole.objects, "filter", return_value=roles_qs) as roles, \
         mock.patch.object(permission.DynamicUser.objects, "filter", return_value=users_qs):
        first = permission.get_dynamic_access("Campus")
        second = permission.get_dynamic_access("Campus")
        assert first == second == {"roles": ["Admins"], "users": ["u-9"]}
        assert roles.call_count == 1

        permission.invalidate_dynamic_access("Campus")
        permission.get_dynamic_access("Campus")
        assert roles.call_count == 2


@override_settings(CACHES=LOCMEM)
def test_dynamic_role_required_allows_listed_role_and_user():
    with mock.patch.object(permission, "get_dynamic_access",
                           return_value={"roles": ["Admins"], "users": ["u-1"]}):
        view = permission.dynamic_role_required("Campus")(lambda obj, request: "allowed")
        assert view(None, _get(token=_token(roles=["Admins"]))) == "allowed"
        assert view(None, _get(token=_token(roles=["Student"]))) == "allowed"  # listed user
        denied = view(None, _get(token=_token(id="u-2", roles=["Student"])))
        assert denied.data["hasError"] is True


# ── outbound requests always have a timeout and fail cleanly ───────────────

def _response(payload=None, status=200, raw=None):
    response = mock.Mock(status_code=status, content=b"")
    if raw is not None:
        response.json.side_effect = ValueError("not json")
    else:
        response.json.return_value = payload
    return response


def test_external_request_sets_timeout_and_parses_once():
    with mock.patch("utils.utils.requests.request", return_value=_response({"ok": 1})) as call:
        response, failure = external_json_request("get", "https://example.invalid", "Partner")
    assert failure is None
    assert response.json() == {"ok": 1}
    assert call.call_args.kwargs["timeout"] is not None


@pytest.mark.parametrize("error", [requests.exceptions.Timeout(), requests.exceptions.ConnectionError()])
def test_external_request_network_failure_returns_failure_response(error):
    with mock.patch("utils.utils.requests.request", side_effect=error):
        response, failure = external_json_request("post", "https://example.invalid", "Partner")
    assert response is None
    assert failure.data["hasError"] is True


def test_external_request_non_json_returns_failure_response():
    with mock.patch("utils.utils.requests.request", return_value=_response(raw=True)):
        response, failure = external_json_request("get", "https://example.invalid", "Partner")
    assert response is None and failure.data["hasError"] is True


# ── launchpad leaderboard id: bare string, lowest pk, None when absent ─────

def test_launchpad_leaderboard_id_is_plain_string():
    from types import SimpleNamespace

    from api.launchpad.serializers import LaunchpadLeaderBoardSerializer

    links = [SimpleNamespace(pk="b", launchpad_id="LP-2"), SimpleNamespace(pk="a", launchpad_id="LP-1")]
    user = SimpleNamespace(launchpad_user=SimpleNamespace(all=lambda: links))
    assert LaunchpadLeaderBoardSerializer().get_launchpad_id(user) == "LP-1"

    empty = SimpleNamespace(launchpad_user=SimpleNamespace(all=lambda: []))
    assert LaunchpadLeaderBoardSerializer().get_launchpad_id(empty) is None
