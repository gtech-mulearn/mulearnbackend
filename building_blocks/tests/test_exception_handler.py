import pytest
from django.db import connection, transaction
from django.http import Http404
from django.test import Client, override_settings
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
        (exceptions.MethodNotAllowed("PATCH"), 405),
    ],
)
def test_a_legacy_views_framework_errors_keep_drfs_response(error, status):
    response = call(view_raising(error, module="api.dashboard.views"))

    assert response.status_code == status
    assert set(response.data) == {"detail"}


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (exceptions.NotFound(), 404, "not_found"),
        (Http404(), 404, "not_found"),
        (exceptions.PermissionDenied(), 403, "forbidden"),
        (exceptions.MethodNotAllowed("PATCH"), 405, "method_not_allowed"),
        (exceptions.UnsupportedMediaType("text/plain"), 415, "unsupported_media_type"),
        (exceptions.ParseError(), 400, "parse_error"),
        (exceptions.Throttled(wait=5), 429, "rate_limited"),
    ],
)
def test_a_module_views_framework_errors_render_the_envelope(error, status, code):
    response = call(view_raising(error))

    assert response.status_code == status
    assert response.data["code"] == code
    assert response.data["statusCode"] == status
    assert response.data["requestId"] == "req_0123456789abcdef0123456789abcdef"
    assert response.data["message"]["general"]


def test_a_throttled_envelope_keeps_retry_after():
    response = call(view_raising(exceptions.Throttled(wait=5)))

    assert response["Retry-After"] == "5"


def test_a_token_failure_in_a_module_view_keeps_its_body():
    body = {"hasError": True, "message": {"general": ["Token Expired or Invalid"]}, "statusCode": 1000}

    response = call(view_raising(TokenFailure(body, 403)))

    assert response.status_code == 403
    assert response.data == body


def test_an_unhandled_exception_is_left_to_django():
    # DRF re-raises when the handler returns None, so Django's middleware logs it (the error log)
    # and Django keeps its own statuses, such as 400 for SuspiciousOperation.
    with pytest.raises(RuntimeError, match="boom"):
        call(view_raising(RuntimeError("boom"), module="api.dashboard.views"))
    with pytest.raises(RuntimeError, match="boom"):
        call(view_raising(RuntimeError("boom")))


@override_settings(ROOT_URLCONF="building_blocks.tests.urls_errors", DEBUG=False)
def test_django_renders_an_unhandled_exception_as_a_json_500_envelope():
    response = Client(raise_request_exception=False).get("/crash/")

    assert response.status_code == 500
    assert response["Content-Type"] == "application/json"
    body = response.json()
    assert body["code"] == "internal_error"
    assert body["hasError"] is True
    assert body["statusCode"] == 500
    assert body["message"] == {"general": ["Something went wrong. Please try again."], "fields": {}}
    assert body["requestId"] == response["X-Request-Id"]


@override_settings(ROOT_URLCONF="building_blocks.tests.urls_errors", DEBUG=False)
def test_djangos_own_400s_stay_400():
    response = Client(raise_request_exception=False).get("/suspicious/")

    assert response.status_code == 400


def test_the_root_urlconf_renders_500s_as_json():
    from mulearnbackend import urls

    assert urls.handler500 == "building_blocks.api.exceptions.server_error"


def test_a_list_of_errors_from_a_many_serializer_is_indexed_under_fields():
    error = exceptions.ValidationError([{"first_name": ["This field is required."]}, {}])

    response = call(view_raising(error))

    assert response.data["message"] == {
        "general": [],
        "fields": {"0": {"firstName": ["This field is required."]}},
    }


def test_errors_of_a_nested_many_serializer_are_camel_cased():
    error = exceptions.ValidationError({"kids": [{"first_name": ["Required."]}]})

    response = call(view_raising(error))

    assert response.data["message"]["fields"] == {"kids": [{"firstName": ["Required."]}]}


@pytest.mark.django_db
def test_an_envelope_marks_the_transaction_for_rollback(monkeypatch):
    # As DRF's own handler does, under ATOMIC_REQUESTS: a failed request's writes don't commit.
    monkeypatch.setitem(connection.settings_dict, "ATOMIC_REQUESTS", True)
    with transaction.atomic():
        exception_handler(NotBookmarkable(), {})
        assert connection.needs_rollback


def test_the_handler_needs_no_view():
    response = exception_handler(NotBookmarkable(), {})

    assert isinstance(response, Response)
    assert response.status_code == 409
