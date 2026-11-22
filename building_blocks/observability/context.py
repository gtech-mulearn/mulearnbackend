"""The current request's id and user id, for log lines and error envelopes.

RequestContextMiddleware sets the request id for each request and clears both values after it.
Code that authenticates a user calls bind_user_id. Never put personal data here: ids only.
"""

from contextvars import ContextVar

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id: ContextVar[str | None] = ContextVar("user_id", default=None)


def current_request_id() -> str | None:
    return request_id.get()


def current_user_id() -> str | None:
    return user_id.get()


def bind_user_id(value: str | None) -> None:
    """Record the authenticated user's id for the rest of the current request."""
    user_id.set(value)
