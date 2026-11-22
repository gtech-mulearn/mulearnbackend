"""Give every request an id, put it in the context, and return it in X-Request-Id."""

import re

from building_blocks.ids import uuid7
from building_blocks.observability import context

HEADER = "X-Request-Id"
INCOMING_FORMAT = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def new_request_id() -> str:
    return "req_" + uuid7().hex


class RequestContextMiddleware:
    """First in MIDDLEWARE, so every response carries X-Request-Id.

    A well-formed incoming X-Request-Id is kept, so a client or proxy can follow its own id;
    anything else is replaced. Both context values are cleared after the response, so nothing
    leaks into the next request on the same thread.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get(HEADER, "")
        rid = incoming if INCOMING_FORMAT.fullmatch(incoming) else new_request_id()
        request.request_id = rid
        rid_token = context.request_id.set(rid)
        user_token = context.user_id.set(None)
        try:
            response = self.get_response(request)
        finally:
            context.request_id.reset(rid_token)
            context.user_id.reset(user_token)
        response[HEADER] = rid
        return response
