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


# ── auth proxies: _forward_to_auth (pass 2) ────────────────────────────────

def _auth_reply(payload=None, status=200, not_json=False):
    response = mock.Mock(status_code=status)
    if not_json:
        response.json.side_effect = requests.exceptions.JSONDecodeError("x", "doc", 0)
    else:
        response.json.return_value = payload
    return response


def _forward(reply=None, error=None, success_message="Access Granted"):
    from api.auth.auth_views import _forward_to_auth

    patch = mock.patch("api.auth.auth_views.requests.post",
                       side_effect=error) if error else mock.patch(
        "api.auth.auth_views.requests.post", return_value=reply)
    with patch as call:
        result = _forward_to_auth("/api/v1/auth/x/", {"a": 1}, "Authentication failed", success_message)
    return result, call


def _general(result):
    return result.data["message"]["general"][0]


def test_auth_proxy_success_keeps_message_and_payload():
    result, call = _forward(_auth_reply({"hasError": False, "response": {"accessToken": "t"}}))
    assert result.data["hasError"] is False
    assert result.data["response"] == {"accessToken": "t"}
    assert _general(result) == "Access Granted"
    assert call.call_args.kwargs["timeout"] == (5, 30)


def test_auth_proxy_upstream_error_message_is_passed_through():
    result, _ = _forward(_auth_reply({"hasError": True, "message": {"general": ["Invalid password"]}}, 400))
    assert result.data["hasError"] is True and _general(result) == "Invalid password"


@pytest.mark.parametrize("reply", [
    {"detail": "Bad gateway"},                    # error status, no hasError key
    {"hasError": True, "message": "oops"},        # message is not a dict
    {"hasError": True, "message": {"general": []}},
    ["not", "a", "dict"],
])
def test_auth_proxy_bad_upstream_bodies_fail_cleanly(reply):
    result, _ = _forward(_auth_reply(reply, 502))
    assert result.data["hasError"] is True and _general(result) == "Authentication failed"


def test_auth_proxy_timeout_and_non_json():
    result, _ = _forward(error=requests.exceptions.Timeout())
    assert _general(result) == "Authentication server timeout"
    result, _ = _forward(_auth_reply(not_json=True, status=502))
    assert result.data["hasError"] is True


# ── pass 2, batch 5: skills, mentor ratings ────────────────────────────────

def _active_skills(stored, requested):
    from utils.utils import active_skill_ids

    with mock.patch("db.skill.Skill.objects") as objects:
        objects.filter.return_value.values_list.return_value = stored
        return active_skill_ids(requested), objects


def test_active_skill_ids_keeps_order_drops_unknown_and_repeats():
    result, objects = _active_skills(["s-1", "s-3"], ["s-3", "nope", "s-1", "S-3"])
    # one query; order kept; a repeat (in any case) dropped, since
    # task_skill_link is unique on (task_id, skill_id)
    assert result == ["s-3", "s-1"]
    objects.filter.assert_called_once_with(id__in=["s-3", "nope", "s-1", "S-3"], is_active=True)


def test_active_skill_ids_matches_case_insensitively_like_mysql():
    result, _ = _active_skills(["s-1"], ["S-1"])
    assert result == ["S-1"]


def test_active_skill_ids_empty_input_runs_no_query():
    result, objects = _active_skills([], [])
    assert result == [] and not objects.filter.called


def test_task_skills_uses_prefetch_when_present():
    from types import SimpleNamespace
    from utils.utils import task_skills

    link = SimpleNamespace(skill=SimpleNamespace(id="s-1", name="Python", code="PY"))
    task = SimpleNamespace(id="t-1", _prefetched_objects_cache={"skill_links": [link]},
                           skill_links=SimpleNamespace(all=lambda: [link]))
    with mock.patch("db.skill.TaskSkillLink.objects") as objects:
        assert task_skills(task) == [{"id": "s-1", "name": "Python", "code": "PY"}]
    assert not objects.filter.called


def test_mentor_rating_map_path_matches_combined_formula():
    from types import SimpleNamespace
    from api.dashboard.mentor.serializers import MentorDetailSerializer

    combine = MentorDetailSerializer._combine_ratings
    assert combine({"avg": None, "count": 0}, {"avg": None, "count": 0}) == {"avg_rating": None, "rating_count": 0}
    # 3 session ratings averaging 4.0 and 1 company rating of 2.0 -> 3.5 over 4
    assert combine({"avg": 4.0, "count": 3}, {"avg": 2.0, "count": 1}) == {"avg_rating": 3.5, "rating_count": 4}

    serializer = MentorDetailSerializer(context={"rating_map": {
        "u-1": ({"avg": 5.0, "count": 1}, {"avg": None, "count": 0}),
    }})
    obj = SimpleNamespace(user_id="u-1")
    with mock.patch("db.mentor.MentorshipSessionUserLink.objects") as objects:
        assert serializer.get_avg_rating(obj) == 5.0
        assert serializer.get_rating_count(obj) == 1
    assert not objects.filter.called  # the page's map is used, no per-row query


# ── pass 2, batch 6: Launchpad helpers ─────────────────────────────────────

def test_college_link_picks_lowest_pk_college_case_insensitively():
    from types import SimpleNamespace
    from api.launchpad.serializers import college_link

    def link(pk, org_type):
        return SimpleNamespace(pk=pk, org=SimpleNamespace(org_type=org_type))
    links = [link("c", "College"), link("a", "Company"), link("b", "college")]
    user = SimpleNamespace(user_organization_link_user=SimpleNamespace(all=lambda: links))
    assert college_link(user).pk == "b"  # was .filter(org__org_type="College").first()
    user = SimpleNamespace(user_organization_link_user=SimpleNamespace(all=lambda: [link("a", "Company")]))
    assert college_link(user) is None


def test_work_ranks_one_query_for_all_karma_values():
    from api.launchpad.launchpad_views import work_ranks_for_karma

    with mock.patch("api.launchpad.launchpad_views.Wallet.objects") as objects:
        objects.filter.return_value.aggregate.return_value = {"k0": 9, "k1": 2}
        assert work_ranks_for_karma([500, 100, 500]) == {100: 10, 500: 3}
    objects.filter.return_value.aggregate.assert_called_once()
    assert set(objects.filter.return_value.aggregate.call_args.kwargs) == {"k0", "k1"}


def test_work_ranks_empty_page_runs_no_query():
    from api.launchpad.launchpad_views import work_ranks_for_karma

    with mock.patch("api.launchpad.launchpad_views.Wallet.objects") as objects:
        assert work_ranks_for_karma([]) == {}
    assert not objects.filter.called


def test_status_counts_is_one_aggregate_with_every_status():
    from api.launchpad.launchpad_views import APPLICATION_STATUSES, status_counts

    qs = mock.Mock()
    status_counts(qs, extra=mock.sentinel.extra)
    qs.aggregate.assert_called_once()
    assert set(qs.aggregate.call_args.kwargs) == {"total", "extra", *APPLICATION_STATUSES}


# ── pass 2, batch 7: smaller areas ─────────────────────────────────────────

def test_rule_engine_ci_equal_matches_mysql_comparison():
    from api.dashboard.achievement.rule_engine import _ci_equal

    assert _ci_equal("#Task-01", "#task-01")
    assert not _ci_equal("#task-01", "#task-02")
    assert _ci_equal(None, None)  # task__hashtag=None is IS NULL
    assert not _ci_equal(None, "#task-01") and not _ci_equal("#task-01", None)


def test_error_log_handler_is_reused_until_the_file_changes(tmp_path):
    from api.dashboard.error_log.log_helper import get_log_handler

    path = tmp_path / "error.log"
    path.write_text("first\n")
    first = get_log_handler(str(path))
    assert get_log_handler(str(path)) is first
    path.write_text("first\nsecond line\n")  # size changes, so the stamp does
    assert get_log_handler(str(path)) is not first
    assert get_log_handler(str(path)).log_data.endswith("second line\n")


def test_error_log_handler_missing_file_raises_ioerror(tmp_path):
    from api.dashboard.error_log.log_helper import get_log_handler

    with pytest.raises(IOError):
        get_log_handler(str(tmp_path / "missing.log"))


def test_kkem_ig_karma_sums_by_exact_name_and_counts_approved_only_by_default():
    from api.integrations.kkem.kkem_serializer import KKEMUserSerializer

    rows = [("u1", "ig-a", "AI", 100), ("u1", "ig-b", "AI", 50), ("u1", "ig-c", "ai", 7), ("u2", "ig-a", "AI", 1)]
    with mock.patch("db.task.KarmaActivityLog.objects") as objects:
        chain = objects.filter.return_value.values_list.return_value.annotate.return_value
        chain.order_by.return_value = rows
        result = KKEMUserSerializer.ig_karma_by_user(["u1", "u2"])
        assert result == {"u1": {"AI": 150, "ai": 7}, "u2": {"AI": 1}}
        assert objects.filter.call_args.kwargs["appraiser_approved"] is True
        KKEMUserSerializer.ig_karma_by_user(["u1"], approved_only=False)
        assert "appraiser_approved" not in objects.filter.call_args.kwargs
