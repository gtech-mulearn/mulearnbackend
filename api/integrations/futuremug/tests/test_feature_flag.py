"""
Futuremug shows only when it is configured AND an admin switched it on from
System → Features (plan C Task 17). Grit Meter shares the same flag code.

No database: system_setting rows live in FakeRows. The conftest gives each
test a fresh local-memory cache and the terms/privacy URLs.
"""
from types import SimpleNamespace
from unittest import mock

import jwt
import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from django.urls import resolve
from rest_framework.test import APIRequestFactory

from api.dashboard.feature import feature_views, flags
from api.integrations.futuremug.adapter import FuturemugAdapter
from utils import permission
from utils.types import RoleType

CONFIGURED = {"FUTUREMUG_API_KEY": "fmsso_key", "FUTUREMUG_BASE_URL": "https://newdev.futuremug.com"}
UNCONFIGURED = {**CONFIGURED, "FUTUREMUG_API_KEY": ""}
factory = APIRequestFactory()


class FakeRows:
    """system_setting as a dict; counts reads so caching is observable."""

    def __init__(self):
        self.rows = {}
        self.reads = 0

    def filter(self, key):
        store = self

        class Rows:
            def first(self):
                store.reads += 1
                value = store.rows.get(key)
                return None if value is None else SimpleNamespace(key=key, value=value)

            def update(self, value, updated_at):
                if key not in store.rows:
                    return 0
                store.rows[key] = value
                return 1

        return Rows()

    def create(self, key, value, created_at, updated_at):
        self.rows[key] = value


@pytest.fixture
def rows():
    fake = FakeRows()
    with mock.patch.object(flags.SystemSetting, "objects", fake):
        yield fake


@pytest.fixture
def db_admin():
    """The caller holds a verified, active Admins role link in the database."""
    with mock.patch.object(permission, "holds_verified_role", return_value=True) as check:
        yield check


def bearer(roles=(RoleType.ADMIN.value,)):
    token = jwt.encode({"id": "u-1", "expiry": "2099-01-01 00:00:00+0000", "roles": list(roles)},
                       settings.SECRET_KEY, algorithm="HS256")
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


def call(slug, method="get", data=None, roles=(RoleType.ADMIN.value,)):
    request = getattr(factory, method)(f"/api/v1/dashboard/feature/{slug}/", data, format="json", **bearer(roles))
    return feature_views.FeatureFlagAPI.as_view()(request, slug=slug)


# ── The switch decides, once Futuremug is configured ──────────────────────

def test_futuremug_is_off_until_an_admin_turns_it_on(rows):
    with override_settings(**CONFIGURED):
        assert FuturemugAdapter().is_configured()
        assert not FuturemugAdapter().is_enabled()


def test_flag_on_and_configured_enables_futuremug(rows):
    rows.rows["futuremug_enabled"] = "true"
    with override_settings(**CONFIGURED):
        assert FuturemugAdapter().is_enabled()


def test_flag_on_but_unconfigured_stays_off(rows):
    rows.rows["futuremug_enabled"] = "true"
    with override_settings(**UNCONFIGURED):
        assert not FuturemugAdapter().is_configured()
        assert not FuturemugAdapter().is_enabled()


# ── Reads are cached; writes go through the cache ─────────────────────────

def test_flag_is_read_from_the_db_once_then_cached(rows):
    rows.rows["futuremug_enabled"] = "true"
    assert [flags.is_flag_on("futuremug_enabled", default=False) for _ in range(3)] == [True, True, True]
    assert rows.reads == 1


def test_a_missing_row_uses_the_default_and_is_cached_too(rows):
    assert flags.is_flag_on("grit_meter_enabled", default=True) is True
    assert flags.is_flag_on("grit_meter_enabled", default=True) is True
    assert rows.reads == 1


def test_set_flag_writes_through_the_cache(rows):
    assert flags.is_flag_on("futuremug_enabled", default=False) is False
    flags.set_flag("futuremug_enabled", True)
    assert flags.is_flag_on("futuremug_enabled", default=False) is True
    assert rows.rows["futuremug_enabled"] == "true"
    assert rows.reads == 1  # the new value came from the cache, not a second query
    flags.set_flag("futuremug_enabled", False)
    assert rows.rows["futuremug_enabled"] == "false"
    assert flags.is_flag_on("futuremug_enabled", default=False) is False


def test_a_cache_outage_falls_back_to_the_db(rows):
    rows.rows["futuremug_enabled"] = "true"
    with mock.patch.object(flags.cache, "get", side_effect=ConnectionError("redis down")), \
         mock.patch.object(flags.cache, "set", side_effect=ConnectionError("redis down")):
        assert flags.is_flag_on("futuremug_enabled", default=False) is True


# ── The API behind System → Features ──────────────────────────────────────

def test_admin_can_enable_a_configured_futuremug(rows, db_admin):
    with override_settings(**CONFIGURED):
        response = call("futuremug", "post", {"enabled": True})
        assert response.status_code == 200
        assert response.data["response"] == {"enabled": True}
        assert response.data["message"]["general"] == ["Futuremug has been successfully enabled."]
        assert FuturemugAdapter().is_enabled()


def test_admin_cannot_enable_an_unconfigured_futuremug(rows, db_admin):
    with override_settings(**UNCONFIGURED):
        response = call("futuremug", "post", {"enabled": True})
    assert response.status_code == 400
    assert response.data["message"]["general"] == [
        "Futuremug isn't configured on this server: set its API key and URLs first."]
    assert "futuremug_enabled" not in rows.rows
    assert flags.is_flag_on("futuremug_enabled", default=False) is False


def test_an_unconfigured_futuremug_can_still_be_switched_off(rows, db_admin):
    rows.rows["futuremug_enabled"] = "true"
    with override_settings(**UNCONFIGURED):
        response = call("futuremug", "post", {"enabled": False})
    assert response.status_code == 200
    assert rows.rows["futuremug_enabled"] == "false"


def test_get_reports_whether_futuremug_is_configured(rows):
    with override_settings(**CONFIGURED):
        assert call("futuremug").data["response"] == {"enabled": False, "configured": True}
    cache.clear()
    with override_settings(**UNCONFIGURED):
        assert call("futuremug").data["response"] == {"enabled": False, "configured": False}


def test_grit_meter_keeps_its_url_default_and_message(rows, db_admin):
    match = resolve("/api/v1/dashboard/feature/grit-meter/")
    assert match.func.view_class is feature_views.FeatureFlagAPI
    assert match.kwargs == {"slug": "grit-meter"}
    assert call("grit-meter").data["response"] == {"enabled": True}  # no row: on, and no "configured"
    response = call("grit-meter", "post", {"enabled": True})
    assert response.data["message"]["general"] == ["Grit Meter system has been successfully enabled."]
    assert rows.rows["grit_meter_enabled"] == "true"


def test_enabled_must_be_a_boolean(rows, db_admin):
    response = call("grit-meter", "post", {"enabled": "yes"})
    assert response.status_code == 400
    assert rows.rows == {}


def test_unknown_flag_is_404(rows, db_admin):
    assert call("nope").status_code == 404
    assert call("nope", "post", {"enabled": True}).status_code == 404


def test_a_non_admin_cannot_switch_a_flag(rows, db_admin):
    response = call("futuremug", "post", {"enabled": True}, roles=("Student",))
    assert response.data["hasError"] is True
    assert rows.rows == {}


def test_an_admin_role_only_in_the_token_cannot_switch_a_flag(rows):
    # Signup accepts any role, so the JWT alone isn't proof (verified link required).
    with mock.patch.object(permission, "holds_verified_role", return_value=False) as check, \
         override_settings(**CONFIGURED):
        response = call("futuremug", "post", {"enabled": True})
    check.assert_called_once_with("u-1", [RoleType.ADMIN.value])
    assert response.data["hasError"] is True
    assert rows.rows == {}
