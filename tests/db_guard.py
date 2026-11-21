"""Refuse to run the test suite against a database that could hold real data.

Some legacy tests flush every table of the database they run against, so pytest
must only ever run against SQLite or a local database whose name starts with
``test_``. See docs/architecture/12-testing-and-quality-gates.md.
"""
import pytest

LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "mysql", "db"}
SAFE_RECIPE = (
    'DATABASE_ENGINE=django.db.backends.sqlite3 DATABASE_NAME=":memory:" DATABASE_USER= '
    "DATABASE_PASSWORD= DATABASE_HOST= DATABASE_PORT= python -m pytest <paths> --import-mode=importlib"
)


def assert_safe_test_database(db: dict) -> None:
    """Return if ``db`` (a ``DATABASES["default"]`` dict) is safe to test against; otherwise stop pytest."""
    engine = str(db.get("ENGINE") or "")
    host = str(db.get("HOST") or "")
    name = str(db.get("NAME") or "")
    if engine.endswith("sqlite3"):
        return
    if host in LOCAL_HOSTS and name.startswith("test_"):
        return
    pytest.exit(
        f"Refusing to run tests against database '{name}' on host '{host}'.\n"
        "Some tests flush every table of the database they run against, so tests may only use SQLite "
        "or a local database whose name starts with 'test_'.\n"
        f"Run them safely with:\n  {SAFE_RECIPE}\n"
        "See docs/architecture/12-testing-and-quality-gates.md.",
        returncode=2,
    )
