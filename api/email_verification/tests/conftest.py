"""Keep User.save() side effects (DB deletes, mail) and the real cache out of DB-free tests."""
from unittest import mock

import pytest
from django.core.cache import cache
from django.test import override_settings

LOCMEM = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "email-verification-tests"}}


@pytest.fixture(autouse=True)
def _local_cache():
    # Code, cooldown and revocation keys must never reach the Redis in .env.
    with override_settings(CACHES=LOCMEM):
        cache.clear()
        yield
        cache.clear()


@pytest.fixture(autouse=True)
def _quiet_email_change_handler():
    # The receiver looks this name up at call time, so patching the module
    # attribute silences it. test_signals imports the real function directly.
    with mock.patch("api.email_verification.signals.handle_email_changed"):
        yield
