import pytest
from _pytest.outcomes import Exit

from tests.db_guard import assert_safe_test_database


def database(engine="django.db.backends.mysql", host="localhost", name="test_mulearn"):
    return {"ENGINE": engine, "HOST": host, "NAME": name}


def test_sqlite_is_allowed():
    assert_safe_test_database(database(engine="django.db.backends.sqlite3", host="dev.example.com", name="mulearn"))


@pytest.mark.parametrize("host", ["", "localhost", "127.0.0.1", "mysql", "db"])
def test_local_test_database_is_allowed(host):
    assert_safe_test_database(database(host=host, name="test_mulearn"))


@pytest.mark.parametrize(
    "host, name",
    [
        ("localhost", "mulearn"),
        ("dev.example.com", "test_mulearn"),
        ("", "mulearn"),
    ],
)
def test_unsafe_database_is_refused(host, name):
    with pytest.raises(Exit) as refused:
        assert_safe_test_database(database(host=host, name=name))

    assert refused.value.returncode == 2
    message = refused.value.msg
    assert f"'{name}'" in message
    assert f"'{host}'" in message
    assert "docs/architecture/12-testing-and-quality-gates.md" in message
    assert "DATABASE_ENGINE=django.db.backends.sqlite3" in message
