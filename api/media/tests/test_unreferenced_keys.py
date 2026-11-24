"""The endpoint the media worker's cleanup calls.

referenced_keys() is the only part that touches the database, so it is
replaced here; what is under test is the Api-Key gate, input checks, and
that the answer is "asked about" minus "still referenced".
"""
import pytest
from rest_framework.test import APIRequestFactory

from api.media import views

UUID_A = "7f3c9e2a-1b4d-4c8e-9a10-5d2e6b7c8f90"
UUID_B = "11111111-2222-4333-8444-555555555555"
UUID_C = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
KEY_A = f"interest_group/cover/{UUID_A}.webp"
KEY_B = f"interest_group/icon/{UUID_B}.webp"
KEY_C = f"interest_group/cover/{UUID_C}.webp"
API_KEY = "test-api-key"


@pytest.fixture
def call(settings, monkeypatch):
    settings.BACKEND_API_KEY = API_KEY
    in_use = set()
    asked = []

    def fake_referenced(keys):
        asked.append(list(keys))
        return in_use & set(keys)

    monkeypatch.setattr(views, "referenced_keys", fake_referenced)
    factory = APIRequestFactory()
    view = views.UnreferencedMediaKeysAPI.as_view()

    def _call(payload, api_key=API_KEY):
        headers = {"HTTP_API_KEY": api_key} if api_key is not None else {}
        return view(factory.post("/api/v1/media/unreferenced-keys/", payload, format="json", **headers))

    _call.in_use = in_use
    _call.asked = asked
    return _call


def test_returns_only_keys_nothing_points_at(call):
    call.in_use.add(KEY_A)
    res = call({"keys": [KEY_A, KEY_B, KEY_C]})
    assert res.status_code == 200
    assert res.data["response"]["unreferenced"] == [KEY_B, KEY_C]


def test_all_referenced_gives_empty_list(call):
    call.in_use.update({KEY_A, KEY_B})
    res = call({"keys": [KEY_A, KEY_B]})
    assert res.data["response"]["unreferenced"] == []


def test_repeated_keys_are_asked_and_answered_once(call):
    res = call({"keys": [KEY_A, KEY_A, KEY_B]})
    assert call.asked == [[KEY_A, KEY_B]]
    assert res.data["response"]["unreferenced"] == [KEY_A, KEY_B]


@pytest.mark.parametrize("api_key", [None, "", "wrong"])
def test_refuses_without_the_right_api_key(call, api_key):
    res = call({"keys": [KEY_A]}, api_key=api_key)
    assert res.status_code in (401, 403)
    assert call.asked == []


@pytest.mark.parametrize("payload", [
    {},
    {"keys": []},
    {"keys": "interest_group/cover/x.webp"},
    {"keys": [123]},
    {"keys": [KEY_A, None]},
])
def test_rejects_a_bad_keys_list(call, payload):
    res = call(payload)
    assert res.status_code == 400
    assert res.data["hasError"] is True
    assert call.asked == []


def test_rejects_values_that_are_not_media_keys(call):
    res = call({"keys": [KEY_A, "users/passwords.txt"]})
    assert res.status_code == 400
    assert call.asked == []


def test_rejects_more_than_the_batch_limit(call):
    many = [f"interest_group/cover/{i:08d}-2222-4333-8444-555555555555.webp" for i in range(views.MAX_KEYS_PER_REQUEST + 1)]
    res = call({"keys": many})
    assert res.status_code == 400
    assert call.asked == []
