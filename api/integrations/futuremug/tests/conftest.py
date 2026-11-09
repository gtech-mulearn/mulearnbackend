import pytest
from django.core.cache import cache
from django.test import override_settings

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "futuremug"}}


@pytest.fixture(autouse=True)
def _memory_cache_and_settings():
    with override_settings(CACHES=LOCMEM, FUTUREMUG_TERMS_URL="https://futuremug.example/terms",
                           FUTUREMUG_PRIVACY_URL="https://futuremug.example/privacy"):
        cache.clear()
        yield
