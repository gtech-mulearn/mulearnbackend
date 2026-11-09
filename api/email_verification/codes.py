"""
Email verification codes (spec A §3.2).

One primitive serves signup, verifying an account and changing email. Only an
HMAC of each code is stored, in the default (Redis) cache, and every limit is
enforced here so no caller can forget one.

Requests run concurrently, so every counter is charged atomically before it
is relied on (cache.add is SET NX, cache.incr is INCR): racing requests each
take their own slot instead of sharing one read.
"""
import hashlib
import hmac
import re
import secrets
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from .errors import VerificationError

PURPOSES = frozenset({"signup", "account", "change"})
CODE_LENGTH = 6
CODE_TTL_SECONDS = 600
MAX_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 60
MAX_SENDS_PER_HOUR = 5


class MailDeliveryFailed(Exception):
    """The deliver callback raised. The code was discarded and nothing was charged."""


@dataclass(frozen=True)
class SentCode:
    expires_in: int
    resend_after: int


def _now():
    return int(time.time())


def _code_key(purpose, subject):
    return f"emailcode:code:{purpose}:{subject}"


def _cooldown_key(purpose, subject):
    return f"emailcode:cooldown:{purpose}:{subject}"


def _attempts_key(purpose, subject):
    return f"emailcode:attempts:{purpose}:{subject}"


def _hourly_key(email, hour):
    return f"emailcode:hour:{email}:{hour}"


def _incr(key, ttl):
    """Atomically add one to a counter, creating it with `ttl` if absent."""
    cache.add(key, 0, ttl)
    try:
        return cache.incr(key)
    except ValueError:  # expired between add and incr
        cache.set(key, 1, ttl)
        return 1


def _refund(key):
    try:
        cache.decr(key)
    except ValueError:  # already expired
        pass


def _reserve_cooldown(purpose, subject, now):
    """Claim the resend slot before mailing, so of two racing sends one wins."""
    key = _cooldown_key(purpose, subject)
    deadline = now + RESEND_COOLDOWN_SECONDS
    if cache.add(key, deadline, RESEND_COOLDOWN_SECONDS):
        return key
    held_until = cache.get(key) or 0
    if held_until > now:
        raise VerificationError("code_cooldown", retry_after=held_until - now)
    # The slot's deadline has passed but the cache still holds the key
    # (clock granularity): replace it, still with SET NX.
    cache.delete(key)
    if not cache.add(key, deadline, RESEND_COOLDOWN_SECONDS):
        raise VerificationError("code_cooldown", retry_after=RESEND_COOLDOWN_SECONDS)
    return key


def _digest(purpose, email, code):
    message = f"{purpose}|{email}|{code}".encode()
    return hmac.new(settings.SECRET_KEY.encode(), message, hashlib.sha256).hexdigest()


def send_code(purpose, subject, email, deliver):
    """
    Issue a fresh code for `subject` (normalised email for signup, user id
    otherwise) and pass it to `deliver(code)`, which mails it to `email`.
    Limits are claimed before mailing and refunded if delivery fails.
    """
    if purpose not in PURPOSES:
        raise ValueError(f"unknown purpose {purpose!r}")
    now = _now()
    cooldown_key = _reserve_cooldown(purpose, subject, now)
    hour = now // 3600
    hourly_key = _hourly_key(email, hour)
    if _incr(hourly_key, 3700) > MAX_SENDS_PER_HOUR:
        _refund(hourly_key)
        cache.delete(cooldown_key)
        raise VerificationError("code_rate_limited", retry_after=(hour + 1) * 3600 - now)

    code = f"{secrets.randbelow(10 ** CODE_LENGTH):0{CODE_LENGTH}d}"
    record = {
        "digest": _digest(purpose, email, code),
        "email": email,
        "expires_at": now + CODE_TTL_SECONDS,
    }
    cache.set(_code_key(purpose, subject), record, CODE_TTL_SECONDS)
    cache.delete(_attempts_key(purpose, subject))  # a new code gets fresh attempts
    try:
        deliver(code)
    except Exception as exc:
        cache.delete(_code_key(purpose, subject))
        cache.delete(cooldown_key)
        _refund(hourly_key)
        raise MailDeliveryFailed() from exc
    return SentCode(expires_in=CODE_TTL_SECONDS, resend_after=RESEND_COOLDOWN_SECONDS)


def revoke_codes(subject, purposes=("account", "change")):
    """Drop codes still waiting for `subject`; an email change makes them stale."""
    cache.delete_many([_code_key(purpose, subject) for purpose in purposes])


def verify_code(purpose, subject, code):
    """Consume a correct code and return the email it was sent to."""
    key = _code_key(purpose, subject)
    record = cache.get(key)
    now = _now()
    if not record or record["expires_at"] <= now:
        cache.delete(key)
        raise VerificationError("code_expired")
    # Charge the attempt before comparing. The counter outlives a dead code
    # (until the code's own expiry), so a racing read can't reopen it.
    attempts = _incr(_attempts_key(purpose, subject), max(record["expires_at"] - now, 1))
    if attempts > MAX_ATTEMPTS:
        cache.delete(key)
        raise VerificationError("invalid_code", attempts_left=0)
    # People paste codes as "123 456" or "123-456"; only the digits count.
    candidate = re.sub(r"\D", "", str(code or ""))
    expected = record["digest"]
    if len(candidate) == CODE_LENGTH and hmac.compare_digest(_digest(purpose, record["email"], candidate), expected):
        cache.delete(key)
        return record["email"]
    attempts_left = MAX_ATTEMPTS - attempts
    if attempts_left <= 0:
        cache.delete(key)
    raise VerificationError("invalid_code", attempts_left=attempts_left)
