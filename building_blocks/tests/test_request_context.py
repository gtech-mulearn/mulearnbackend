import re
import uuid

import pytest
from django.conf import settings
from django.http import HttpResponse
from django.test import Client, RequestFactory

from building_blocks.observability import context
from building_blocks.observability.middleware import RequestContextMiddleware

GENERATED = re.compile(r"^req_[0-9a-f]{32}$")


def run(header=None):
    """Pass one request through the middleware; return the response and the id the view saw."""
    seen = {}

    def view(request):
        seen["context"] = context.current_request_id()
        seen["request"] = request.request_id
        return HttpResponse("ok")

    extra = {} if header is None else {"HTTP_X_REQUEST_ID": header}
    response = RequestContextMiddleware(view)(RequestFactory().get("/", **extra))
    return response, seen


@pytest.mark.parametrize("incoming", ["abcd1234", "req_01936b2e5b7e", "A-b_C-d_" * 8])
def test_a_valid_incoming_id_is_kept(incoming):
    response, seen = run(incoming)

    assert response["X-Request-Id"] == incoming
    assert seen == {"context": incoming, "request": incoming}


@pytest.mark.parametrize(
    "incoming",
    ["", "short", "x" * 65, "has space1", "semi;colon1", "abcd1234\r\nSet-Cookie: a=b", "ünïcödé123"],
)
def test_a_bad_incoming_id_is_replaced(incoming):
    response, seen = run(incoming)

    assert response["X-Request-Id"] != incoming
    assert GENERATED.fullmatch(response["X-Request-Id"])
    assert seen["context"] == response["X-Request-Id"]


def test_a_missing_id_is_generated_from_a_uuid7():
    response, _ = run()
    request_id = response["X-Request-Id"]

    assert GENERATED.fullmatch(request_id)
    assert uuid.UUID(hex=request_id.removeprefix("req_")).version == 7


def test_each_request_gets_its_own_id():
    assert run()[0]["X-Request-Id"] != run()[0]["X-Request-Id"]


def test_the_context_is_cleared_after_the_response():
    run("abcd1234")

    assert context.current_request_id() is None
    assert context.current_user_id() is None


def test_the_context_is_cleared_when_the_view_raises():
    def view(request):
        context.bind_user_id("user-1")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        RequestContextMiddleware(view)(RequestFactory().get("/"))

    assert context.current_request_id() is None
    assert context.current_user_id() is None


def test_the_middleware_runs_first():
    assert settings.MIDDLEWARE[0] == "building_blocks.observability.middleware.RequestContextMiddleware"


def test_every_response_carries_the_header_through_the_full_stack():
    # A route that doesn't exist: the response comes from Django's 404 handling, after every middleware.
    response = Client().get("/no-such-route-for-0018/", HTTP_X_REQUEST_ID="abcd1234")

    assert response.status_code == 404
    assert response["X-Request-Id"] == "abcd1234"
