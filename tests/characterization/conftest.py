"""Fixtures for characterization tests (issue 0025, docs/architecture/12-testing-and-quality-gates.md).

    def test_my_route(make_user, api_client, assert_envelope, golden, django_assert_num_queries):
        user = make_user(roles=["Student"])
        with django_assert_num_queries(5):
            response = api_client(user).get("/api/v1/...")
        assert_envelope(response, has_error=False, status_code=200)
        golden(response, "my_route")

Run with --update-golden to write the golden files, then review them before committing.
"""

import pytest
from rest_framework.test import APIClient

from tests.characterization import factories
from tests.characterization.harness import GOLDEN_DIR, check_golden, envelope_problems, mint_token

LOCAL_CACHES = {
    alias: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": f"characterization-{alias}"}
    for alias in ("default", "redis")
}


@pytest.fixture(autouse=True)
def _fresh_cache(settings):
    """An empty in-memory cache per test, so responses and query counts don't depend on Redis."""
    settings.CACHES = LOCAL_CACHES
    from django.core.cache import caches

    for alias in LOCAL_CACHES:
        caches[alias].clear()


@pytest.fixture
def make_user(db):
    """make_user(roles=(), **fields): a user, its wallet, and a verified link to each role title."""

    def make(roles=(), **fields):
        user = factories.UserFactory(**fields)
        factories.WalletFactory(user=user)
        for title in roles:
            factories.UserRoleLinkFactory(user=user, role=factories.RoleFactory(title=title))
        user.role_titles = list(roles)
        return user

    return make


@pytest.fixture
def api_client():
    """api_client(user, roles=None): an APIClient carrying a valid access token for ``user``."""

    def make(user, roles=None):
        client = APIClient()
        titles = getattr(user, "role_titles", []) if roles is None else roles
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {mint_token(user, titles)}")
        return client

    return make


@pytest.fixture
def assert_envelope():
    """assert_envelope(response, *, has_error, status_code, http_status=status_code)."""

    def check(response, *, has_error, status_code, http_status=None):
        problems = envelope_problems(
            response,
            has_error=has_error,
            status_code=status_code,
            http_status=status_code if http_status is None else http_status,
        )
        assert not problems, "The response envelope differs: " + "; ".join(problems)

    return check


@pytest.fixture
def golden(request):
    """golden(response, name): compare the normalised body with tests/characterization/golden/<name>.json."""
    update = request.config.getoption("--update-golden")

    def check(response, name):
        check_golden(response.json(), GOLDEN_DIR / f"{name}.json", update=update)

    return check
