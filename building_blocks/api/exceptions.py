"""One exception handler for the API (issue 0019, ADR-010, docs/architecture/07-api-standards.md).

REST_FRAMEWORK["EXCEPTION_HANDLER"] points here, and the root URLconf's handler500 at server_error.

- **A DomainError** renders the envelope with its ``code`` and ``http_status``.
- **A DRF ValidationError with status 400** renders 400, ``code: validation_error``, with the field
  messages under ``message.fields`` (camelCase) and non-field ones under ``message.general``.
- **DRF's other errors** (not found, method not allowed, unsupported media type, parse error,
  permission, throttling) render the envelope too, with a code for their status.
- **Legacy views keep DRF's own responses** for everything above except a DomainError, which
  legacy code never raises. A legacy response may gain only ``code`` and ``requestId``, and DRF's
  bodies aren't envelopes. Legacy views are told apart by their module (``api``, ``db``,
  ``utils``, ``mu_celery``): building_blocks never imports legacy code.
- **Token failures keep their response everywhere.** utils.exception.UnauthorizedAccessException
  is a ValidationError raised with status 401 or 403 and a ``statusCode 1000`` body, which old
  clients refresh their token on. Only a status-400 ValidationError counts as a validation error.
- **Anything unhandled is left to Django** (the handler returns None, so DRF re-raises it): the
  error-log middleware records it, and Django keeps its own statuses (400 for SuspiciousOperation
  and BadRequest). Django then renders the 500 with server_error, a JSON envelope with
  ``code: internal_error``.
"""

from django.http import Http404, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.views import set_rollback

from building_blocks.errors import DomainError
from building_blocks.observability.context import current_request_id

# Packages whose views keep DRF's own error responses. Named, not imported: building_blocks never
# imports legacy code.
LEGACY_PACKAGES = ("api", "db", "utils", "mu_celery")
INTERNAL_ERROR_MESSAGE = "Something went wrong. Please try again."
# Codes for DRF's errors in module views, by status; any other status uses DRF's own code.
CODES_BY_STATUS = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    429: "rate_limited",
}


def _body(*, http_status: int, code: str, general=None, fields=None) -> dict:
    """The error envelope: the legacy four keys plus code and requestId."""
    return {
        "hasError": True,
        "statusCode": http_status,
        "code": code,
        "message": {"general": list(general or []), "fields": dict(fields or {})},
        "response": {},
        "requestId": current_request_id(),
    }


def envelope(*, http_status: int, code: str, general=None, fields=None, headers=None) -> Response:
    set_rollback()  # as DRF's own handler does: a failed request's writes don't commit
    return Response(
        _body(http_status=http_status, code=code, general=general, fields=fields), status=http_status, headers=headers
    )


def server_error(request) -> JsonResponse:
    """handler500: Django's 500, as a JSON envelope instead of an HTML page."""
    return JsonResponse(
        _body(http_status=500, code="internal_error", general=[INTERNAL_ERROR_MESSAGE]),
        status=500,
    )


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def _messages(value):
    if isinstance(value, dict):
        return {_camel(str(key)): _messages(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_messages(item) if isinstance(item, dict | list) else str(item) for item in value]
    return [str(value)]


def _validation_message(detail) -> tuple[list, dict]:
    """(general, fields) from a ValidationError's detail: a dict of fields, a list, or a string."""
    if isinstance(detail, dict):
        general = [str(item) for item in detail.get("non_field_errors", [])]
        fields = {_camel(str(key)): _messages(value) for key, value in detail.items() if key != "non_field_errors"}
        return general, fields
    if isinstance(detail, list):
        if any(isinstance(item, dict) for item in detail):
            # A many=True serializer: one entry per item, keyed by its index.
            return [], {str(index): _messages(item) for index, item in enumerate(detail) if item}
        return [str(item) for item in detail], {}
    return [str(detail)], {}


def _from_legacy_view(context) -> bool:
    view = context.get("view") if context else None
    return view is not None and type(view).__module__.split(".")[0] in LEGACY_PACKAGES


def _is_token_failure(exc) -> bool:
    return isinstance(exc, exceptions.ValidationError) and exc.status_code != status.HTTP_400_BAD_REQUEST


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return envelope(http_status=exc.http_status, code=exc.code, general=[exc.public_message])

    if _from_legacy_view(context) or _is_token_failure(exc):
        return drf_exception_handler(exc, context)

    if isinstance(exc, exceptions.ValidationError):
        general, fields = _validation_message(exc.detail)
        return envelope(http_status=400, code="validation_error", general=general, fields=fields)

    response = drf_exception_handler(exc, context)
    if response is None:
        return None  # unhandled: DRF re-raises, and Django logs it and renders server_error
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    code = CODES_BY_STATUS.get(response.status_code) or getattr(exc, "default_code", "domain_error")
    detail = response.data.get("detail") if isinstance(response.data, dict) else None
    headers = {name: value for name, value in response.items() if name in ("WWW-Authenticate", "Retry-After")}
    return envelope(
        http_status=response.status_code,
        code=code,
        general=[str(detail)] if detail else [],
        headers=headers,
    )
