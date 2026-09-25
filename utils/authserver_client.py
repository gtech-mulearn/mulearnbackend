"""
Client for authserver's internal API (/api/v1/internal/).

mulearnbackend no longer writes user.password, revokes sessions by writing
authserver's Redis keys, or touches the OAuth tables. It asks authserver, which
owns all three. Authenticated with the shared PROTECTED_API_KEY, the same key
authserver already uses to call this service's provision-member endpoint.
"""

import logging

import decouple
import requests

logger = logging.getLogger(__name__)

# (connect, read). Every one of these calls has a person waiting on it, and a
# timeout-free call to another service is how audit finding F14 happened.
TIMEOUT = (3, 10)


class AuthServerUnavailable(Exception):
    """authserver could not be reached or answered with something unusable."""


def call(method, path, *, json=None, params=None):
    """
    One internal API call. Returns (http_status, body_dict).

    4xx responses are returned, not raised: they carry an error code and a
    message meant for the person (wrong current password, invalid policy).

    :raises AuthServerUnavailable: network failure, 5xx, or a body that is not a JSON object.
    """
    url = f"{decouple.config('AUTH_DOMAIN').rstrip('/')}/api/v1/internal/{path.lstrip('/')}"
    try:
        response = requests.request(
            method,
            url,
            json=json,
            params=params,
            headers={"protectionKey": decouple.config("PROTECTED_API_KEY")},
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        logger.exception("authserver internal call failed: %s %s", method, path)
        raise AuthServerUnavailable("The sign-in service is unavailable. Please try again.") from exc

    try:
        body = response.json()
    except ValueError as exc:
        logger.error("authserver returned non-JSON for %s %s: HTTP %s", method, path, response.status_code)
        raise AuthServerUnavailable("The sign-in service returned an unexpected response.") from exc

    # Every internal endpoint answers with a JSON object; callers rely on that
    # for body.get(). A list, string or null means something in between (a
    # proxy, a misroute) answered instead.
    if not isinstance(body, dict):
        logger.error("authserver returned a non-object body for %s %s: HTTP %s", method, path, response.status_code)
        raise AuthServerUnavailable("The sign-in service returned an unexpected response.")

    if response.status_code >= 500 and response.status_code != 503:
        logger.error("authserver error for %s %s: HTTP %s %s", method, path, response.status_code, body)
        raise AuthServerUnavailable("The sign-in service returned an error. Please try again.")

    return response.status_code, body


def error_message(body, default="The request could not be completed."):
    """The person-safe message from an authserver error body."""
    if isinstance(body, dict):
        return body.get("error_description") or default
    return default
