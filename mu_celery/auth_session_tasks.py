"""
Make sure "sign this member out everywhere" eventually happens.

Used when a password was set but authserver reported the session revocation as
incomplete. The reset link is already consumed by then (it must never be able
to set a second password), so the retry has to happen here rather than by the
person resubmitting the link.

Three pieces, so an incomplete revocation is never just dropped:

  1. A Redis hash of pending user ids. Written BEFORE the task is queued and
     removed only when authserver confirms the revocation. It lives in the
     same Redis as the Celery queue, so it is exactly as durable as the queued
     task itself.
  2. revoke_all_sessions: the fast path, retried with backoff for about an
     hour. Giving up there leaves the user in the hash.
  3. retry_pending_session_revocations (beat, every 15 minutes): retries every
     pending user and never gives up. Anything pending over an hour is logged
     as an error on every run until it clears or an admin revokes it by hand
     (dashboard: Auth Admin -> revoke sessions).

The hash is bounded: one field per member, removed on success.
"""

import logging
import time

from celery import shared_task
from django.core.cache import cache
from django_redis import get_redis_connection

from utils.authserver_client import AuthServerUnavailable, call

logger = logging.getLogger(__name__)

PENDING_KEY = "auth:session_revoke_pending"

# 1, 2, 4, 8, 15, 15, 15, 15 minutes: a little over an hour in total.
MAX_RETRIES = 8
MAX_DELAY_SECONDS = 15 * 60

ALERT_AFTER_SECONDS = 60 * 60
SWEEP_BATCH = 200
SWEEP_LOCK_KEY = "auth_session_revoke_sweep_lock"
SWEEP_LOCK_TIMEOUT = 60 * 10


def _pending():
    return get_redis_connection("default")


def mark_pending(user_id):
    """Record that this member still has sessions to revoke. Keeps the first time."""
    _pending().hsetnx(PENDING_KEY, str(user_id), int(time.time()))


def _clear_pending(user_id):
    _pending().hdel(PENDING_KEY, str(user_id))


def _revoke_once(user_id):
    """
    One attempt. Returns True when done (confirmed, or the user no longer
    exists), False when it should be tried again.
    """
    try:
        status, body = call("POST", "sessions/revoke/", json={"user_id": user_id})
    except AuthServerUnavailable:
        return False

    if status == 200 and body.get("sessions_revoked"):
        _clear_pending(user_id)
        logger.info("Sessions revoked for %s", user_id)
        return True
    if status == 404:
        _clear_pending(user_id)
        logger.error("Session revocation: user %s not found in authserver", user_id)
        return True
    return False


@shared_task(bind=True, max_retries=MAX_RETRIES)
def revoke_all_sessions(self, user_id):
    """Idempotent: revoking already-revoked sessions is a no-op in authserver."""
    if _revoke_once(user_id):
        return True
    try:
        raise self.retry(countdown=min(60 * 2 ** self.request.retries, MAX_DELAY_SECONDS))
    except self.MaxRetriesExceededError:
        logger.error(
            "Session revocation for %s still incomplete after %s retries; "
            "left pending for the 15-minute sweep", user_id, MAX_RETRIES,
        )
        return False


@shared_task
def retry_pending_session_revocations():
    """
    Returns how many were still pending after this run, or -1 if a run was
    already in progress.
    """
    if not cache.add(SWEEP_LOCK_KEY, "1", SWEEP_LOCK_TIMEOUT):
        return -1
    try:
        pending = _pending().hgetall(PENDING_KEY)
        now = time.time()
        still_pending = 0
        for raw_user_id, raw_since in list(pending.items())[:SWEEP_BATCH]:
            user_id = raw_user_id.decode()
            if _revoke_once(user_id):
                continue
            still_pending += 1
            if now - int(raw_since) > ALERT_AFTER_SECONDS:
                logger.error(
                    "Sessions for %s still not revoked %s minutes after a password "
                    "reset; revoke them from the admin console",
                    user_id, int((now - int(raw_since)) // 60),
                )
        return still_pending + max(0, len(pending) - SWEEP_BATCH)
    finally:
        cache.delete(SWEEP_LOCK_KEY)
