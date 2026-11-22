"""Domain errors with stable codes and HTTP statuses (ADR-010, docs/architecture/07-api-standards.md).

Framework-free: domain code raises these, and one exception handler (issue 0019) renders
them into the response envelope. A module registers each of its errors:

    @error_code("events.not_bookmarkable", "Event can't be bookmarked")
    class NotBookmarkable(Conflict):
        public_message = "Cancelled or past events cannot be bookmarked."

Registered codes are a public contract: clients branch on them, so removing or renaming one
is a breaking change. They are "<module>.<code>", lowercase letters and underscores.
"""

import re

CODE_FORMAT = re.compile(r"^[a-z_]+\.[a-z_]+$")

_registry: dict[str, type["DomainError"]] = {}


class DomainError(Exception):
    """A failure the client can act on. Subclass a category below, then register it."""

    code = "domain_error"
    http_status = 400
    title = "Request failed"
    public_message = "The request could not be completed."

    def __init__(self, public_message: str | None = None):
        if public_message is not None:
            self.public_message = public_message
        super().__init__(self.public_message)


class ValidationFailed(DomainError):
    code = "validation_error"
    http_status = 400
    title = "Invalid input"
    public_message = "Some of the input is invalid."


class Unauthorized(DomainError):
    code = "unauthorized"
    http_status = 401
    title = "Not signed in"
    public_message = "Sign in to continue."


class Forbidden(DomainError):
    code = "forbidden"
    http_status = 403
    title = "Not allowed"
    public_message = "You don't have permission to do this."


class NotFound(DomainError):
    code = "not_found"
    http_status = 404
    title = "Not found"
    public_message = "That doesn't exist."


class Conflict(DomainError):
    code = "conflict"
    http_status = 409
    title = "Conflict"
    public_message = "This conflicts with the current state."


class Unprocessable(DomainError):
    code = "unprocessable"
    http_status = 422
    title = "Can't be processed"
    public_message = "The request is valid but can't be processed."


class RateLimited(DomainError):
    code = "rate_limited"
    http_status = 429
    title = "Too many requests"
    public_message = "Too many requests. Try again later."


class DependencyUnavailable(DomainError):
    code = "dependency_unavailable"
    http_status = 503
    title = "Temporarily unavailable"
    public_message = "A service this needs is unavailable. Try again later."


def error_code(code: str, title: str):
    """Register a DomainError subclass under ``code``, which must be "<module>.<code>" and unused."""
    if not CODE_FORMAT.fullmatch(code):
        raise ValueError(f"Error code {code!r} must be '<module>.<code>': lowercase letters and underscores.")
    if not title.strip():
        raise ValueError(f"Error code {code!r} needs a title.")

    def register(cls):
        if not (isinstance(cls, type) and issubclass(cls, DomainError)):
            raise TypeError(f"@error_code({code!r}) decorates DomainError subclasses only, not {cls!r}.")
        if code in _registry:
            raise ValueError(f"Error code {code!r} is already used by {_registry[code].__qualname__}.")
        if cls in _registry.values():
            raise ValueError(f"{cls.__qualname__} is already registered as {cls.code!r}.")
        cls.code = code
        cls.title = title
        _registry[code] = cls
        return cls

    return register


def registry() -> dict[str, type[DomainError]]:
    """Every registered error, by code. A copy: register with @error_code."""
    return dict(_registry)
