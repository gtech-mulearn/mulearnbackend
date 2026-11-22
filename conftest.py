"""Root pytest conftest.

The db.* models are all `managed = False` and the project ships no migrations,
so Django has to be set up explicitly before any test module imports a model.
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()


def pytest_configure(config):
    """Stop before collection unless the database is safe to test against.

    Called from the hook, not at import time: pytest.exit raised while a conftest is
    being imported ends with exit code 4 and a traceback instead of code 2.
    """
    from django.conf import settings

    from tests.db_guard import assert_safe_test_database

    assert_safe_test_database(settings.DATABASES["default"])
