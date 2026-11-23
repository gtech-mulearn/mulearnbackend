"""CustomResponse gains code and requestId, and nothing else changes (issue 0019)."""

from building_blocks.observability import context
from utils.response import CustomResponse

RID = "req_0123456789abcdef0123456789abcdef"


def render(method, *args, **kwargs):
    token = context.request_id.set(RID)
    try:
        return method(*args, **kwargs)
    finally:
        context.request_id.reset(token)


def test_success_gains_code_ok_and_the_request_id():
    response = render(CustomResponse(general_message="Done", response={"a": 1}).get_success_response)

    assert response.status_code == 200
    assert response.data == {
        "hasError": False,
        "statusCode": 200,
        "message": {"general": ["Done"]},
        "response": {"a": 1},
        "code": "ok",
        "requestId": RID,
    }


def test_failure_gains_the_given_code_or_domain_error():
    default = render(CustomResponse(general_message="Bad").get_failure_response)
    gone = CustomResponse(general_message="Gone")
    named = render(gone.get_failure_response, status_code=404, http_status_code=404, code="not_found")

    assert default.status_code == 400
    assert default.data == {
        "hasError": True,
        "statusCode": 400,
        "message": {"general": ["Bad"]},
        "response": {},
        "code": "domain_error",
        "requestId": RID,
    }
    assert named.status_code == 404
    assert named.data["code"] == "not_found"
    assert named.data["statusCode"] == 404


def test_unauthorized_gains_code_forbidden():
    response = render(CustomResponse(general_message="No").get_unauthorized_response)

    assert response.status_code == 403
    assert response.data["statusCode"] == 403
    assert response.data["code"] == "forbidden"
    assert response.data["requestId"] == RID


def test_a_paginated_response_gains_code_ok():
    response = render(CustomResponse().paginated_response, data=[1], pagination={"count": 1})

    assert response.data["code"] == "ok"
    assert response.data["response"] == {"data": [1], "pagination": {"count": 1}}


def test_outside_a_request_the_request_id_is_none():
    assert CustomResponse().get_success_response().data["requestId"] is None


def test_a_failure_without_a_code_names_its_status():
    codes = {
        status: render(CustomResponse().get_failure_response, status_code=status).data["code"]
        for status in (400, 401, 403, 404, 409, 422, 429, 500)
    }

    assert codes == {
        400: "domain_error",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "unprocessable",
        429: "rate_limited",
        500: "internal_error",
    }


def test_a_cached_response_gets_the_current_request_id(settings):
    # An in-memory cache: CI has no Redis.
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    from django.core.cache import cache

    from utils.utils import cache_view_response

    cache.delete("test-0019-cache")

    class View:
        @cache_view_response("test-0019-cache", timeout=60)
        def get(self, request):
            return CustomResponse(response={"a": 1}).get_success_response()

    first = render(View().get, None)
    token = context.request_id.set("req_ffffffffffffffffffffffffffffffff")
    try:
        second = View().get(None)
    finally:
        context.request_id.reset(token)
        cache.delete("test-0019-cache")

    assert first.data["requestId"] == RID
    assert second.data["requestId"] == "req_ffffffffffffffffffffffffffffffff"
    assert second.data["response"] == {"a": 1}
