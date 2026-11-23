"""The characterization harness itself, on the unit tier (issue 0025)."""

import json
from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from tests.characterization.harness import check_golden, envelope_problems, mint_token, normalise
from utils.permission import JWTUtils

USER = SimpleNamespace(id="0b5c3f5e-8a2d-4c41-9d0e-2f1a3b4c5d6e", muid="person@mulearn")


def response(body, status=200):
    return SimpleNamespace(status_code=status, json=lambda: body)


def test_a_minted_token_passes_the_backends_own_check():
    token = mint_token(USER, roles=["Student"])
    request = RequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

    _, payload = JWTUtils.is_jwt_authenticated(request)

    assert payload["id"] == USER.id
    assert payload["muid"] == USER.muid
    assert payload["roles"] == ["Student"]


def test_an_expired_token_is_refused_by_the_backend():
    token = mint_token(USER, roles=[], expires_in_seconds=-60)
    request = RequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

    with pytest.raises(Exception, match="Expired"):
        JWTUtils.is_jwt_authenticated(request)


def test_normalise_replaces_request_ids():
    assert normalise({"requestId": "req_0193a1b2c3d4e5f60718293a4b5c6d7e"}) == {"requestId": "<request-id>"}
    assert normalise({"note": "req_short"}) == {"note": "req_short"}


def test_normalise_replaces_ids_and_timestamps_only():
    body = {
        "id": "0b5c3f5e-8a2d-4c41-9d0e-2f1a3b4c5d6e",
        "joined": "2026-11-22T04:30:00.123456Z",
        "updated": "2026-11-22T10:00:00+05:30",
        "day": "2026-11-22",
        "karma": 120,
        "name": "Person",
        "pic": None,
        "tags": ["a", "0b5c3f5e-8a2d-4c41-9d0e-2f1a3b4c5d6e"],
    }

    assert normalise(body) == {
        "id": "<uuid>",
        "joined": "<datetime>",
        "updated": "<datetime>",
        "day": "2026-11-22",
        "karma": 120,
        "name": "Person",
        "pic": None,
        "tags": ["a", "<uuid>"],
    }


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ({"a": 1}, {"a": 1, "b": 2}),  # a field added
        ({"a": 1, "b": 2}, {"a": 1}),  # a field removed
        ({"a": 1}, {"a": "1"}),  # a type changed
        ({"a": "0b5c3f5e-8a2d-4c41-9d0e-2f1a3b4c5d6e"}, {"a": None}),  # an id became null
        ({"a": [1, 2]}, {"a": [2, 1]}),  # an order changed
    ],
)
def test_normalisation_never_hides_a_shape_change(before, after):
    assert normalise(before) != normalise(after)


def test_a_matching_golden_passes(tmp_path):
    path = tmp_path / "x.json"
    path.write_text(json.dumps({"a": "<uuid>"}), encoding="utf-8")

    check_golden({"a": "0b5c3f5e-8a2d-4c41-9d0e-2f1a3b4c5d6e"}, path, update=False)


def test_a_changed_response_fails_with_a_readable_diff(tmp_path):
    path = tmp_path / "x.json"
    check_golden({"karma": 1, "name": "A"}, path, update=True)

    with pytest.raises(AssertionError) as failure:
        check_golden({"karma": 1, "name": "B", "extra": True}, path, update=False)

    message = str(failure.value)
    assert '-  "name": "A"' in message
    assert '+  "name": "B"' in message
    assert '+  "extra": true' in message
    assert "--update-golden" in message


def test_a_missing_golden_fails_instead_of_being_created(tmp_path):
    path = tmp_path / "absent.json"

    with pytest.raises(AssertionError, match="--update-golden"):
        check_golden({"a": 1}, path, update=False)
    assert not path.exists()


def test_update_rewrites_the_golden_file(tmp_path):
    path = tmp_path / "x.json"
    check_golden({"b": 2, "a": "2026-11-22T04:30:00Z"}, path, update=True)

    assert json.loads(path.read_text(encoding="utf-8")) == {"a": "<datetime>", "b": 2}
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_envelope_problems_are_listed():
    ok = response({"hasError": False, "statusCode": 200, "message": {}, "response": {}})
    assert envelope_problems(ok, has_error=False, status_code=200, http_status=200) == []

    bad = response({"hasError": True, "statusCode": 1000, "message": {}}, status=403)
    problems = envelope_problems(bad, has_error=False, status_code=200, http_status=200)
    assert problems == [
        "missing key 'response'",
        "hasError is True, expected False",
        "statusCode is 1000, expected 200",
        "HTTP status is 403, expected 200",
    ]
