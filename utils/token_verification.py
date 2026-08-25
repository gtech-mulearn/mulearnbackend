"""
Token verification: new RS256 alongside legacy HS256.

Django-free so it can be unit-tested without settings or a database
(see utils/test_token_verification.py).

Why both formats
----------------
Every client cannot switch at once. This service must accept the new
asymmetric tokens AND the ones already in people's browsers, for one full
refresh-token lifetime, or moving any client logs everyone out. The legacy
branch is deleted only when the counter below shows zero legacy validations for
seven consecutive days - observed, not assumed.

What changes between the formats
--------------------------------
    legacy HS256                    new RS256
    -----------------------------   ---------------------------------
    signed with a SHARED secret,    signed with a private key held only
    so any verifier can also mint   by authserver; verified with a public key
    "expiry" as a formatted string  standard "exp", enforced by the library
    "id" holds the user id          "sub" holds the user id
    "roles" embedded in the token   absent - resolved from the database
    "muid" embedded in the token    absent - resolved from the database

The shared-secret property is the reason for all of this: under HS256 every
service that can check a token can also forge one, so a second app cannot be
added safely.

Audit finding F10 is fixed here too. fetch_role, fetch_user_id and fetch_muid
each used to decode the token separately, and none of them validated expiry -
only is_jwt_authenticated did. A caller reaching for a claim directly got an
unvalidated read. Verification now happens once and every claim comes from that
single validated payload.
"""

import logging
import time

import jwt
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

FORMAT_LEGACY = "legacy_hs256"
FORMAT_OIDC = "oidc_rs256"

# JWKS is fetched over the network, so it must never be fetched per request.
# Keys rotate rarely and a `kid` miss forces a refresh anyway, so a long TTL is
# safe and a short one is a self-inflicted denial of service.
JWKS_CACHE_SECONDS = 3600


class TokenError(Exception):
    """The token cannot be trusted. The message is safe to log, not to echo."""


class _JWKSCache:
    """
    Caches authserver's public keys.

    Deliberately a small object rather than a module global so tests can hold
    their own instance and not leak state between cases.
    """

    def __init__(self, jwks_url, ttl=JWKS_CACHE_SECONDS, client_factory=None):
        self.jwks_url = jwks_url
        self.ttl = ttl
        self._client_factory = client_factory or PyJWKClient
        self._client = None
        self._fetched_at = 0.0

    def signing_key(self, token, *, now=None):
        now = time.time() if now is None else now
        if self._client is None or (now - self._fetched_at) > self.ttl:
            self._client = self._client_factory(self.jwks_url)
            self._fetched_at = now
        return self._client.get_signing_key_from_jwt(token).key


def token_format(token):
    """
    Which format a token claims to be, read from its UNVERIFIED header.

    Only ever used to choose a verification path. The header is attacker
    controlled, so this must not be treated as a fact - claiming RS256 simply
    routes the token to the RS256 verifier, which then rejects it if the
    signature does not hold. Crucially, a token claiming HS256 is verified with
    the shared secret and NEVER with a public key: that confusion is the classic
    attack asymmetric signing invites.
    """
    try:
        alg = jwt.get_unverified_header(token).get("alg", "")
    except jwt.PyJWTError:
        return None
    if alg == "RS256":
        return FORMAT_OIDC
    if alg == "HS256":
        return FORMAT_LEGACY
    return None


def verify_oidc_token(token, *, jwks_cache, issuer, audience, leeway=0):
    """
    Verify a new-format token. Expiry, issuer and audience are enforced by the
    library rather than by hand.
    """
    try:
        key = jwks_cache.signing_key(token)
    except Exception as exc:
        # Fail CLOSED. If the keys cannot be fetched we cannot prove the token
        # is genuine, and "allow it through" would make an outage at authserver
        # into an authentication bypass here.
        raise TokenError("Could not retrieve signing keys") from exc

    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=issuer,
            audience=audience,
            leeway=leeway,
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc


def verify_legacy_token(token, *, secret, now):
    """
    Verify a legacy token, including the hand-rolled expiry.

    The legacy format carries `expiry` as a formatted string rather than a
    standard `exp`, so the library cannot enforce it and this function must.
    That is precisely why F10 was possible: any caller that decoded without
    repeating this check accepted expired tokens.

    :param now: timezone-aware current time, injected so this is testable.
    """
    from datetime import datetime

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise TokenError(f"Invalid token: {exc}") from exc

    raw_expiry = payload.get("expiry")
    if not raw_expiry:
        raise TokenError("Token has no expiry")

    try:
        expiry = datetime.strptime(raw_expiry, "%Y-%m-%d %H:%M:%S%z")
    except (ValueError, TypeError) as exc:
        raise TokenError("Token expiry is malformed") from exc

    if expiry < now:
        raise TokenError("Token expired")

    if not payload.get("id"):
        raise TokenError("Token has no subject")

    return payload


def normalise(payload, fmt):
    """
    One shape for both formats, so callers never branch on which they got.

    `roles` and `muid` are None for new-format tokens: they are muLearn's data,
    not identity data, and the resource server resolves them from its own
    database. That is what makes a role change take effect immediately instead
    of whenever a token happens to expire.
    """
    if fmt == FORMAT_OIDC:
        return {
            "user_id": payload.get("sub"),
            "muid": None,
            "roles": None,
            "scope": (payload.get("scope") or "").split(),
            "format": fmt,
            "raw": payload,
        }
    return {
        "user_id": payload.get("id"),
        "muid": payload.get("muid"),
        "roles": payload.get("roles"),
        "scope": [],
        "format": fmt,
        "raw": payload,
    }
