import socket
import time

from scripts.check_test_mysql import main


def mysql_env(name="test_mulearn", port="3306"):
    return {
        "DATABASE_ENGINE": "django.db.backends.mysql",
        "DATABASE_HOST": "127.0.0.1",
        "DATABASE_PORT": port,
        "DATABASE_NAME": name,
    }


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return str(s.getsockname()[1])


def test_a_non_test_database_is_refused_by_the_guard(capsys):
    assert main(mysql_env(name="mulearn")) == 2
    assert "Refusing to run tests against database 'mulearn'" in capsys.readouterr().err


def test_an_unreachable_server_fails_fast_with_a_hint(capsys):
    started = time.monotonic()
    assert main(mysql_env(port=free_port())) == 1
    assert time.monotonic() - started < 10
    assert "Can't reach MySQL at 127.0.0.1:" in capsys.readouterr().err


def test_a_listening_server_passes():
    with socket.socket() as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        assert main(mysql_env(port=str(server.getsockname()[1]))) == 0
