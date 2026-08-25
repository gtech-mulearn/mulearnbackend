"""
Session revocation on credential change (audit finding F3).

Background: changing or resetting a password did not invalidate existing
sessions. A refresh token stolen before the change kept minting access tokens
for up to 7 days afterwards — so password reset, the primary account-recovery
control a user has, did not actually recover the account.

Mechanism: `authserver` rejects any refresh token whose `iat` is at or before
`global_logout:{user_id}` in Redis. Writing that key here invalidates every
outstanding session for the identity.

INTENTIONAL COUPLING — READ BEFORE EXTENDING.
This writes a key owned by `authserver` directly, rather than calling an
authserver endpoint. That is deliberate for this fix: both services already
share one Redis instance and database index (`redis://…/1`, see each
settings.py), it is the smallest change that closes a High-severity gap inside
the pre-GA window, and Part 2 replaces the whole mechanism with database-backed
refresh tokens. The key format is mirrored from
`authserver/muauth/views.py::RedisRevocationStore`; if one changes, change both.
Do not add further cross-service cache writes on the strength of this one.
"""

import logging

from django.core.cache import caches

logger = logging.getLogger(__name__)

# Must match authserver/muauth/views.py::RedisRevocationStore.
GLOBAL_LOGOUT_KEY = "global_logout:{}"
GLOBAL_LOGOUT_TTL_SECONDS = 7 * 24 * 60 * 60  # max refresh-token lifetime


def revoke_all_sessions(user_id, at_timestamp):
    """
    Invalidate every outstanding session for `user_id`.

    Returns True on success, False if the revocation could not be recorded.
    Callers must surface a failure rather than reporting the password change
    as fully successful — silently failing here recreates F3.
    """
    try:
        caches["redis"].set(
            GLOBAL_LOGOUT_KEY.format(user_id),
            int(at_timestamp),
            timeout=GLOBAL_LOGOUT_TTL_SECONDS,
        )
        return True
    except Exception:
        logger.exception("Failed to revoke sessions for user %s", user_id)
        return False
