import pytest
from django.db import OperationalError, connection
from django.test import Client, override_settings

LOCAL_CACHE = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def no_drain(tmp_path, settings):
    settings.DRAIN_FLAG_PATH = str(tmp_path / "mulearn-drain")
    return tmp_path / "mulearn-drain"


def test_live_is_always_200(client):
    response = client.get("/healthz/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_live_is_200_even_while_draining(client, no_drain):
    no_drain.touch()

    assert client.get("/healthz/live").status_code == 200


@pytest.mark.django_db
@override_settings(CACHES=LOCAL_CACHE)
def test_ready_is_200_when_the_database_and_cache_answer(client, no_drain):
    response = client.get("/healthz/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.django_db
@override_settings(CACHES=LOCAL_CACHE)
def test_touching_the_drain_file_makes_ready_503_on_the_next_request(client, no_drain):
    assert client.get("/healthz/ready").status_code == 200

    no_drain.touch()
    response = client.get("/healthz/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "draining"}

    no_drain.unlink()
    assert client.get("/healthz/ready").status_code == 200


@pytest.mark.django_db
@override_settings(CACHES=LOCAL_CACHE)
def test_ready_is_503_when_the_database_check_raises(client, no_drain, monkeypatch):
    def broken():
        raise OperationalError("database unreachable")

    monkeypatch.setattr(connection, "cursor", broken)
    response = client.get("/healthz/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


@pytest.mark.django_db
@override_settings(
    CACHES={"default": {"BACKEND": "django_redis.cache.RedisCache", "LOCATION": "redis://127.0.0.1:1/0"}}
)
def test_ready_is_503_when_the_cache_is_unreachable(client, no_drain):
    response = client.get("/healthz/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


def test_the_drain_flag_defaults_to_tmp():
    from building_blocks.health.drain import DEFAULT_DRAIN_FLAG_PATH

    assert DEFAULT_DRAIN_FLAG_PATH == "/tmp/mulearn-drain"


@pytest.mark.parametrize("path", ["/healthz/live", "/healthz/ready"])
def test_writes_are_refused(client, path):
    assert client.post(path).status_code == 405


@pytest.mark.parametrize("path", ["/healthz/live", "/healthz/ready"])
def test_no_token_is_needed_and_head_works(client, path, no_drain, monkeypatch):
    monkeypatch.setattr("building_blocks.health.views.dependencies_answer", lambda: True)

    assert client.head(path).status_code == 200
