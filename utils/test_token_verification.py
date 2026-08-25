"""
Tests for dual-format token verification.

Standalone under pytest — `utils.token_verification` has no Django imports:

    pytest utils/test_token_verification.py

Every authenticated request in this service flows through this code. The tests
that matter most are the rejections, not the acceptances.
"""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from utils.token_verification import (
    FORMAT_LEGACY,
    FORMAT_OIDC,
    TokenError,
    normalise,
    token_format,
    verify_legacy_token,
    verify_oidc_token,
)

NOW = datetime(2026, 8, 22, 12, 0, 0, tzinfo=timezone.utc)
SECRET = "legacy-shared-secret"
ISSUER = "https://auth.mulearn.org"
AUDIENCE = "mulearn-api"

_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = _key.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.TraditionalOpenSSL,
    serialization.NoEncryption(),
).decode()
PUBLIC_KEY = _key.public_key()


class FakeJWKS:
    """Stands in for authserver's published keys."""

    def __init__(self, key=PUBLIC_KEY, explode=False):
        self.key = key
        self.explode = explode
        self.calls = 0

    def signing_key(self, token, now=None):
        self.calls += 1
        if self.explode:
            raise ConnectionError("authserver unreachable")
        return self.key


def legacy_token(expiry=None, secret=SECRET, **claims):
    payload = {
        "id": "user-uuid-1",
        "muid": "anitha@mulearn",
        "roles": ["Mulearner"],
        "expiry": (expiry or NOW + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S%z"),
    }
    payload.update(claims)
    return jwt.encode(payload, secret, algorithm="HS256")


def oidc_token(exp=None, iss=ISSUER, aud=AUDIENCE, **claims):
    """
    Minted against the REAL clock, not the frozen NOW used by the legacy tests.

    PyJWT enforces `exp` itself, against actual current time — it has no way to
    accept an injected clock. Basing these on a hardcoded NOW made the tests
    pass before that timestamp and fail after it: they went green at 17:45 and
    red at 17:47 with no code change. The legacy tests can keep a frozen NOW
    because verify_legacy_token takes `now` as an argument.
    """
    real_now = datetime.now(timezone.utc)
    payload = {
        "sub": "user-uuid-1",
        "iss": iss,
        "aud": aud,
        "exp": int((exp or real_now + timedelta(minutes=15)).timestamp()),
        "iat": int(real_now.timestamp()),
        "scope": "openid mulearn.read",
    }
    payload.update(claims)
    return jwt.encode(payload, PRIVATE_PEM, algorithm="RS256")


class TestFormatRouting:
    def test_recognises_each_format(self):
        assert token_format(legacy_token()) == FORMAT_LEGACY
        assert token_format(oidc_token()) == FORMAT_OIDC

    def test_garbage_has_no_format(self):
        assert token_format("not-a-jwt") is None

    def test_unexpected_algorithm_is_not_routed_anywhere(self):
        # `none` must never reach a verifier. An unrouted token is rejected by
        # the caller rather than being handed to a branch that might accept it.
        unsigned = jwt.encode({"sub": "x"}, key="", algorithm="none")
        assert token_format(unsigned) is None


class TestOIDC:
    def test_a_valid_token_verifies(self):
        payload = verify_oidc_token(
            oidc_token(), jwks_cache=FakeJWKS(), issuer=ISSUER, audience=AUDIENCE
        )
        assert payload["sub"] == "user-uuid-1"

    def test_expired_is_rejected(self):
        token = oidc_token(exp=datetime.now(timezone.utc) - timedelta(minutes=1))
        with pytest.raises(TokenError):
            verify_oidc_token(token, jwks_cache=FakeJWKS(), issuer=ISSUER, audience=AUDIENCE)

    def test_wrong_issuer_is_rejected(self):
        token = oidc_token(iss="https://evil.example")
        with pytest.raises(TokenError):
            verify_oidc_token(token, jwks_cache=FakeJWKS(), issuer=ISSUER, audience=AUDIENCE)

    def test_wrong_audience_is_rejected(self):
        # A token minted for a DIFFERENT muLearn app must not work here.
        token = oidc_token(aud="some-other-app")
        with pytest.raises(TokenError):
            verify_oidc_token(token, jwks_cache=FakeJWKS(), issuer=ISSUER, audience=AUDIENCE)

    def test_a_token_signed_by_someone_else_is_rejected(self):
        other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = other.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ).decode()
        forged = jwt.encode(
            {"sub": "admin", "iss": ISSUER, "aud": AUDIENCE,
             # NOT expired, so the only reason this can fail is the
             # signature — which is the thing under test.
             "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp())},
            pem, algorithm="RS256",
        )
        with pytest.raises(TokenError):
            verify_oidc_token(forged, jwks_cache=FakeJWKS(), issuer=ISSUER, audience=AUDIENCE)

    def test_missing_required_claims_are_rejected(self):
        token = jwt.encode({"sub": "x", "aud": AUDIENCE}, PRIVATE_PEM, algorithm="RS256")
        with pytest.raises(TokenError):
            verify_oidc_token(token, jwks_cache=FakeJWKS(), issuer=ISSUER, audience=AUDIENCE)

    def test_unreachable_keys_fail_CLOSED(self):
        # If authserver is down we cannot prove anything about the token.
        # Allowing it through would turn an outage into an auth bypass.
        with pytest.raises(TokenError):
            verify_oidc_token(
                oidc_token(), jwks_cache=FakeJWKS(explode=True),
                issuer=ISSUER, audience=AUDIENCE,
            )


class TestLegacy:
    def test_a_valid_token_verifies(self):
        payload = verify_legacy_token(legacy_token(), secret=SECRET, now=NOW)
        assert payload["id"] == "user-uuid-1"

    def test_expired_is_rejected(self):
        # THE F10 CASE. fetch_role and friends decoded without this check, so an
        # expired token still yielded roles. Verification now happens once, here.
        token = legacy_token(expiry=NOW - timedelta(minutes=1))
        with pytest.raises(TokenError):
            verify_legacy_token(token, secret=SECRET, now=NOW)

    def test_wrong_secret_is_rejected(self):
        with pytest.raises(TokenError):
            verify_legacy_token(legacy_token(secret="wrong"), secret=SECRET, now=NOW)

    def test_missing_expiry_is_rejected(self):
        token = jwt.encode({"id": "x", "muid": "m"}, SECRET, algorithm="HS256")
        with pytest.raises(TokenError):
            verify_legacy_token(token, secret=SECRET, now=NOW)

    def test_malformed_expiry_is_rejected(self):
        # Not "treated as never expiring".
        token = jwt.encode({"id": "x", "expiry": "soon"}, SECRET, algorithm="HS256")
        with pytest.raises(TokenError):
            verify_legacy_token(token, secret=SECRET, now=NOW)

    def test_missing_subject_is_rejected(self):
        token = jwt.encode(
            {"expiry": (NOW + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S%z")},
            SECRET, algorithm="HS256",
        )
        with pytest.raises(TokenError):
            verify_legacy_token(token, secret=SECRET, now=NOW)


class TestAlgorithmConfusion:
    def test_an_hs256_token_signed_with_the_public_key_is_not_accepted(self):
        """
        The classic attack asymmetric signing invites: take the PUBLIC key,
        which anyone can fetch from JWKS, use it as an HMAC secret, and hand the
        result to a verifier that trusts the header's `alg`.

        It fails here because the two formats are verified by different
        functions with hardcoded algorithm lists - the RS256 path never accepts
        HS256, and the legacy path only ever uses the shared secret.
        """
        public_pem = PUBLIC_KEY.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        # Forged by hand, because PyJWT REFUSES to build this: it detects an
        # asymmetric key being used as an HMAC secret and raises InvalidKeyError.
        # An attacker has no such scruples and would assemble the bytes
        # directly, so the test must too - otherwise it proves only that our
        # own library is polite, not that our verifier is safe.
        import base64
        import hashlib
        import hmac as hmac_mod
        import json as json_mod

        def b64(raw):
            return base64.urlsafe_b64encode(raw).rstrip(b"=")

        header = b64(json_mod.dumps({"alg": "HS256", "typ": "JWT"}).encode())
        body = b64(json_mod.dumps({
            "sub": "admin", "iss": ISSUER, "aud": AUDIENCE,
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=5)).timestamp()),
        }).encode())
        signing_input = header + b"." + body
        signature = b64(hmac_mod.new(public_pem, signing_input, hashlib.sha256).digest())
        forged = (signing_input + b"." + signature).decode()
        # It routes to the legacy verifier, which uses the real shared secret.
        assert token_format(forged) == FORMAT_LEGACY
        with pytest.raises(TokenError):
            verify_legacy_token(forged, secret=SECRET, now=NOW)


class TestNormalise:
    def test_legacy_carries_roles_and_muid(self):
        payload = verify_legacy_token(legacy_token(), secret=SECRET, now=NOW)
        n = normalise(payload, FORMAT_LEGACY)
        assert n["user_id"] == "user-uuid-1"
        assert n["muid"] == "anitha@mulearn"
        assert n["roles"] == ["Mulearner"]

    def test_oidc_carries_neither_and_says_so(self):
        # None, not [] - "resolve these yourself" must be distinguishable from
        # "this person genuinely has no roles", which would silently strip
        # everyone's permissions.
        payload = verify_oidc_token(
            oidc_token(), jwks_cache=FakeJWKS(), issuer=ISSUER, audience=AUDIENCE
        )
        n = normalise(payload, FORMAT_OIDC)
        assert n["user_id"] == "user-uuid-1"
        assert n["roles"] is None
        assert n["muid"] is None
        assert n["scope"] == ["openid", "mulearn.read"]
