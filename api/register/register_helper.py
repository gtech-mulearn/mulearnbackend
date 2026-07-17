import decouple
import logging
import requests

logger = logging.getLogger(__name__)

from db.user import User

from utils.exception import CustomException


AUTH_TIMEOUT = (3, 10)  # (connect seconds, read seconds) — B4


def generate_muid(full_name):
    full_name = full_name.replace(" ", "").lower()[:85]
    muid = f"{full_name}@mulearn"

    counter = 0

    while User.every.filter(muid=muid).exists():
        counter += 1
        muid = f"{full_name}-{counter}@mulearn"

    return muid


def _post_auth(path, **kwargs):
    """
    Thin wrapper around requests.post that:
    - Adds a connect + read timeout to every outbound call (B4).
    - Converts network-level errors to CustomException so callers
      can return a clean error without orphaning DB rows.
    """
    AUTH_DOMAIN = decouple.config("AUTH_DOMAIN")
    try:
        return requests.post(
            f"{AUTH_DOMAIN}{path}", timeout=AUTH_TIMEOUT, **kwargs
        )
    except requests.RequestException:
        raise CustomException(
            "Auth service is temporarily unavailable. Please try again."
        )


def get_auth_token(muid, password):
    resp = _post_auth(
        "/api/v1/auth/user-authentication/",
        data={"emailOrMuid": muid, "password": password},
    )
    if not resp.ok:
        logger.error(
            "get_auth_token failed: HTTP %s | body: %s",
            resp.status_code, resp.text[:500],
        )
        raise CustomException(
            "Auth service returned an unexpected error. Please try again."
        )
    body = resp.json()
    if body.get("statusCode") != 200:
        raise CustomException(body.get("message"))
    return body.get("response")


def verify_google_temp_token(temp_token):
    """
    Verifies a Google tempToken with the auth server.
    Returns {'email', 'fullName'} or raises CustomException.

    Checks body statusCode rather than HTTP status as defense-in-depth (B1/P4).
    Null-guards the response to avoid KeyError on an unexpected empty body (B1).
    """
    resp = _post_auth(
        "/api/v1/auth/google/verify-temp-token/",
        data={"tempToken": temp_token},
        headers={"protectionKey": decouple.config("PROTECTED_API_KEY")},
    )
    if not resp.ok:
        logger.error(
            "verify_google_temp_token failed: HTTP %s | body: %s",
            resp.status_code, resp.text[:500],
        )
        raise CustomException(
            "Auth service returned an unexpected error. Please try again."
        )
    body = resp.json()
    if body.get("statusCode") != 200:
        raise CustomException(
            body.get("message")
            or "Invalid or expired Google session. Please sign in with Google again."
        )
    data = body.get("response") or {}
    if not data.get("email"):
        raise CustomException("Google verification returned no email.")
    return data


def get_auth_token_by_id(user_id):
    """
    Gets JWT tokens for a user by their UUID using the internal
    TokenVerificationAPI endpoint.
    Used for Google sign-ups where no password is set (NULL).
    """
    resp = _post_auth(
        f"/api/v1/auth/token-verification/{user_id}/",
        headers={"protectionKey": decouple.config("PROTECTED_API_KEY")},
    )
    if not resp.ok:
        logger.error(
            "get_auth_token_by_id failed: HTTP %s | body: %s",
            resp.status_code, resp.text[:500],
        )
        raise CustomException(
            "Auth service returned an unexpected error. Please try again."
        )
    body = resp.json()
    if body.get("statusCode") != 200:
        raise CustomException(body.get("message"))
    return body.get("response")