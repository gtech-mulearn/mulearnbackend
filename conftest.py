"""Root pytest conftest.

The db.* models are all `managed = False` and the project ships no migrations,
so Django has to be set up explicitly before any test module imports a model.

On the MySQL tier (scripts/test.sh --mysql), tests run against the test database as it
was loaded from schema/latest.sql, and the system user is kept in place.
"""
import os
from pathlib import Path

import django
import pytest
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mulearnbackend.settings")
django.setup()

SEED_SYSTEM_USER = Path(__file__).resolve().parent / "scripts" / "seed-system-user.sql"
MYSQL_TIER = settings.DATABASES["default"]["ENGINE"].endswith("mysql")


def pytest_addoption(parser):
    # Declared here, not in tests/characterization/conftest.py: pytest only registers options
    # from the conftest files it loads at startup.
    parser.addoption(
        "--update-golden",
        action="store_true",
        help="Rewrite tests/characterization/golden/ from the current responses, then review the diff.",
    )


def pytest_configure(config):
    """Stop before collection unless the database is safe to test against.

    Called from the hook, not at import time: pytest.exit raised while a conftest is
    being imported ends with exit code 4 and a traceback instead of code 2.
    """
    from tests.db_guard import assert_safe_test_database

    assert_safe_test_database(settings.DATABASES["default"])

    # Django removal warnings raised in new code are errors; legacy code only warns (tests/deprecations.py).
    from tests.deprecations import error_filters

    for line in error_filters():
        config.addinivalue_line("filterwarnings", line)


def pytest_terminal_summary(terminalreporter):
    """Count the Django removal warnings left, all from legacy code; CI's legacy job reports it."""
    from tests.deprecations import count_removal_warnings

    count = count_removal_warnings(terminalreporter.stats.get("warnings", []))
    terminalreporter.write_line(f"Django deprecation warnings from legacy code: {count}")


def ensure_system_user():
    """Apply scripts/seed-system-user.sql if the system user is missing.

    The backend refuses to start without the user whose id is SYSTEM_ADMIN_ID (db/apps.py),
    and a transaction=True test commits whatever it deletes.
    """
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM user WHERE id = %s", [settings.SYSTEM_ADMIN_ID])
        if cursor.fetchone() is None:
            cursor.execute(SEED_SYSTEM_USER.read_text(encoding="utf-8"))


if MYSQL_TIER:
    from django.contrib.auth.management import create_permissions
    from django.contrib.contenttypes.management import create_contenttypes
    from django.db.models.signals import post_migrate

    # After each transaction=True test, Django flushes the database and sends post_migrate.
    # The contenttypes and auth receivers then query django_content_type and auth_permission,
    # which the schema doesn't have: the project has no migrations.
    post_migrate.disconnect(create_contenttypes)
    post_migrate.disconnect(create_permissions, dispatch_uid="django.contrib.auth.management.create_permissions")

    @pytest.fixture(scope="session")
    def django_db_setup():
        """Use the loaded test database as it is.

        pytest-django would create an empty test_<name> database instead: every model is
        managed = False and there are no migrations, so it would have no tables.
        """

    @pytest.fixture(autouse=True)
    def _system_user(request, django_db_blocker):
        if request.node.get_closest_marker("mysql"):
            with django_db_blocker.unblock():
                ensure_system_user()

    def pytest_sessionfinish(session):
        # So the next run can start: db/apps.py checks for the system user at django.setup().
        from pytest_django.plugin import blocking_manager_key

        with session.config.stash[blocking_manager_key].unblock():
            ensure_system_user()
