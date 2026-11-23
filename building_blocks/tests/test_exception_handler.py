import logging

import pytest
from django.http import Http404
from rest_framework import exceptions
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from building_blocks.api.exceptions import exception_handler
from building_blocks.errors import Conflict, error_code
from building_blocks.observability import context

factory = APIRequestFactory()


@error_code("testing.not_bookmarkable", "Event can't be bookmarked")
class NotBookmarkable(Conflict):
    public_message = "Cancelled or past events cannot be bookmarked."


def view_raising(error, module="modules.events.api.views"):
    """A test-only view in a module of our choosing (a module path, or a legacy one)."""

    class RaisingView(APIView):
        authentication_classes = []
        permission_classes = []

        def get(self, request):
            raise error

    RaisingView.__module__ = module
    return RaisingView.as_view()


def call(view):
    token = context.request_id.set("req_0123456789abcdef0123456789abcdef")
    try:
        return view(factory.get("/test/"))
    finally:
        context.request_id.reset(token)


def test_the_handler_is_the_rest_framework_one(settings):
    assert settings.REST_FRAMEWORK["EXCEPTION_HANDLER"] == "building_blocks.api.exceptions.exception_handler"


def test_a_domain_error_renders_the_envelope_with_its_code_and_status():
    response = call(view_raising(NotBookmarkable()))

    assert response.status_code == 409
    assert response.data == {
        "hasError": True,
        "statusCode": 409,
        "code": "testing.not_bookmarkable",
        "message": {"general": ["Cancelled or past events cannot be bookmarked."], "fields": {}},
        "response": {},
        "requestId": "req_0123456789abcdef0123456789abcdef",
    }


def test_a_validation_error_renders_400_with_the_field_messages_in_camel_case():
    error = exceptions.ValidationError({"starts_at": ["Must be in the future."], "non_field_errors": ["Bad dates."]})

    response = call(view_raising(error))

    assert response.status_code == 400
    assert response.data["code"] == "validation_error"
    assert response.data["statusCode"] == 400
    assert response.data["message"] == {"general": ["Bad dates."], "fields": {"startsAt": ["Must be in the future."]}}
    assert response.data["requestId"] == "req_0123456789abcdef0123456789abcdef"


def test_a_validation_error_given_as_a_list_goes_to_general():
    response = call(view_raising(exceptions.ValidationError(["Pick one."])))

    assert response.data["message"] == {"general": ["Pick one."], "fields": {}}


def test_a_legacy_views_validation_error_keeps_its_response():
    # The compatibility promise: a legacy response gains nothing but code and requestId, and a raw
    # DRF validation body isn't an envelope, so it stays exactly as it was.
    response = call(view_raising(exceptions.ValidationError(["Pick one."]), module="api.dashboard.views"))

    assert response.status_code == 400
    assert response.data == ["Pick one."]


class TokenFailure(exceptions.ValidationError):
    """Like utils.exception.UnauthorizedAccessException: a ValidationError with a raw body and 401 or 403."""

    def __init__(self, detail, status_code=403):
        self.detail = detail
        self.status_code = status_code


@pytest.mark.parametrize("status_code", [401, 403])
def test_a_token_failure_keeps_its_status_and_body(status_code):
    body = {"hasError": True, "message": {"general": ["Token Expired or Invalid"]}, "statusCode": 1000}
    error = TokenFailure(body, status_code)

    response = call(view_raising(error))

    assert response.status_code == status_code
    assert response.data == body


@pytest.mark.parametrize(
    ("error", "status"),
    [
        # DRF itself answers 403, not 401, when the view has no authenticators, as this one has none.
        (exceptions.NotAuthenticated(), 403),
        (exceptions.AuthenticationFailed(), 403),
        (exceptions.PermissionDenied(), 403),
        (Http404(), 404),
        (exceptions.Throttled(wait=5), 429),
    ],
)
def test_other_framework_errors_keep_drfs_response(error, status):
    response = call(view_raising(error))

    assert response.status_code == status
    assert set(response.data) == {"detail"}


def test_an_unhandled_exception_renders_a_json_500_and_is_logged(caplog):
    with caplog.at_level(logging.ERROR, logger="building_blocks.api"):
        response = call(view_raising(RuntimeError("boom")))

    assert response.status_code == 500
    assert response.data == {
        "hasError": True,
        "statusCode": 500,
        "code": "internal_error",
        "message": {"general": ["Something went wrong. Please try again."], "fields": {}},
        "response": {},
        "requestId": "req_0123456789abcdef0123456789abcdef",
    }
    assert any(record.exc_info and "boom" in str(record.exc_info[1]) for record in caplog.records)


def test_an_unhandled_exception_in_a_legacy_view_is_a_json_500_too():
    response = call(view_raising(KeyError("x"), module="api.dashboard.views"))

    assert response.status_code == 500
    assert response.data["code"] == "internal_error"


def test_the_handler_needs_no_view():
    response = exception_handler(NotBookmarkable(), {})

    assert isinstance(response, Response)
    assert response.status_code == 409
