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
