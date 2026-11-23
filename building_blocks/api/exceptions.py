"""One exception handler for the API (issue 0019, ADR-010, docs/architecture/07-api-standards.md).

REST_FRAMEWORK["EXCEPTION_HANDLER"] points here.

- **A DomainError** renders the envelope with its ``code`` and ``http_status``.
- **A DRF ValidationError with status 400** raised by a view outside the legacy packages renders
  400, ``code: validation_error``, with the field messages under ``message.fields`` (camelCase)
  and non-field ones under ``message.general``.
- **Everything else DRF handles keeps DRF's response exactly:** authentication, permission, not
  found and throttling errors; the legacy token failures (utils.exception.UnauthorizedAccessException
  is a ValidationError raised with status 401 or 403, and old clients refresh their token on its
  ``statusCode 1000`` body); and a legacy view's own validation errors. A legacy response may gain
  only ``code`` and ``requestId``, and these bodies aren't envelopes.
- **Anything unhandled** is logged with its traceback and renders a JSON 500 envelope with
  ``code: internal_error``, instead of Django's HTML error page.
"""

import logging

from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from building_blocks.errors import DomainError
from building_blocks.observability.context import current_request_id

logger = logging.getLogger("building_blocks.api")

# Packages whose views keep DRF's own error responses. Named, not imported: building_blocks never
# imports legacy code.
LEGACY_PACKAGES = ("api", "db", "utils", "mu_celery")
INTERNAL_ERROR_MESSAGE = "Something went wrong. Please try again."


def envelope(*, http_status: int, code: str, general=None, fields=None) -> Response:
    """The error envelope: the legacy four keys plus code and requestId."""
    return Response(
        {
            "hasError": True,
            "statusCode": http_status,
            "code": code,
            "message": {"general": list(general or []), "fields": dict(fields or {})},
            "response": {},
            "requestId": current_request_id(),
        },
        status=http_status,
    )


def _camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest)


def _messages(value) -> list | dict:
    if isinstance(value, dict):
        return {_camel(str(key)): _messages(item) for key, item in value.items()}
    if isinstance(value, list):
        return [item if isinstance(item, dict) else str(item) for item in value]
    return [str(value)]


def _validation_message(detail) -> tuple[list, dict]:
    """(general, fields) from a ValidationError's detail: a dict of fields, a list or a string."""
    if isinstance(detail, dict):
        general = [str(item) for item in detail.get("non_field_errors", [])]
        fields = {_camel(str(key)): _messages(value) for key, value in detail.items() if key != "non_field_errors"}
        return general, fields
    if isinstance(detail, list):
        return [str(item) for item in detail], {}
    return [str(detail)], {}


def _from_legacy_view(context) -> bool:
    view = context.get("view") if context else None
    return view is not None and type(view).__module__.split(".")[0] in LEGACY_PACKAGES


def exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return envelope(http_status=exc.http_status, code=exc.code, general=[exc.public_message])

    is_validation = isinstance(exc, exceptions.ValidationError) and exc.status_code == status.HTTP_400_BAD_REQUEST
    if is_validation and not _from_legacy_view(context):
        general, fields = _validation_message(exc.detail)
        return envelope(http_status=400, code="validation_error", general=general, fields=fields)

    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    logger.error("unhandled exception in %s", _view_name(context), exc_info=(type(exc), exc, exc.__traceback__))
    return envelope(
        http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        general=[INTERNAL_ERROR_MESSAGE],
    )


def _view_name(context) -> str:
    view = context.get("view") if context else None
    return f"{type(view).__module__}.{type(view).__qualname__}" if view is not None else "a request"
