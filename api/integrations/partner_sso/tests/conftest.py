"""Partner SSO tests touch the cache (rate limits, locks): keep it in memory."""
import pytest
from django.core.cache import cache
from django.test import override_settings

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "partner-sso"}}


@pytest.fixture(autouse=True)
def _memory_cache():
    with override_settings(CACHES=LOCMEM):
        cache.clear()
        yield
        cache.clear()
