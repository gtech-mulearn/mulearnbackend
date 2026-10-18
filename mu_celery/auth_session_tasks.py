"""
Make sure "sign this member out everywhere" eventually happens.

Used when a password was set but authserver reported the session revocation as
incomplete. The reset link is already consumed by then (it must never be able
to set a second password), so the retry has to happen here rather than by the
person resubmitting the link.

Three pieces, so an incomplete revocation is never just dropped:

  1. A pending record in Redis. Written BEFORE the task is queued and removed
     only when authserver confirms the revocation. It lives in the same Redis
     as the Celery queue, so it is exactly as durable as the queued task.
  2. revoke_all_sessions: the fast path, retried with backoff for about an
     hour. Giving up there leaves the record in place.
  3. retry_pending_session_revocations (beat, every 15 minutes): retries
     pending members and never gives up. Anything pending over an hour is
     logged as an error on every attempt until it clears or an admin revokes
     it by hand (dashboard: Auth Admin -> revoke sessions).

The record is two keys:
  QUEUE_KEY  sorted set, member = user id, score = last attempt time.
             Each sweep takes the least recently attempted batch and moves
             failures to the back, so every pending member is reached in turn
             however many keep failing.
  SINCE_KEY  hash, user id -> when it first went pending (for the alert).
Both are bounded: one entry per member, removed on success.
"""

import logging
import time

from celery import shared_task
from django.core.cache import cache
from django_redis import get_redis_connection

from utils.authserver_client import AuthServerUnavailable, call

logger = logging.getLogger(__name__)

QUEUE_KEY = "auth:session_revoke_queue"
SINCE_KEY = "auth:session_revoke_since"

# 1, 2, 4, 8, 15, 15, 15, 15 minutes: a little over an hour in total.
MAX_RETRIES = 8
MAX_DELAY_SECONDS = 15 * 60

ALERT_AFTER_SECONDS = 60 * 60
SWEEP_BATCH = 200
SWEEP_LOCK_KEY = "auth_session_revoke_sweep_lock"
SWEEP_LOCK_TIMEOUT = 60 * 10

# _revoke_once outcomes
DONE, FAILED, UNAVAILABLE = "done", "failed", "unavailable"


def _redis():
    return get_redis_connection("default")


def mark_pending(user_id, *, now=None):
    """Record that this member still has sessions to revoke. Keeps the first time."""
    now = int(time.time() if now is None else now)
    pipe = _redis().pipeline()
    pipe.hsetnx(SINCE_KEY, str(user_id), now)
    pipe.zadd(QUEUE_KEY, {str(user_id): now}, nx=True)
    pipe.execute()


def _clear_pending(user_id):
    pipe = _redis().pipeline()
    pipe.zrem(QUEUE_KEY, str(user_id))
    pipe.hdel(SINCE_KEY, str(user_id))
    pipe.execute()


def _revoke_once(user_id):
    try:
        status, body = call("POST", "sessions/revoke/", json={"user_id": user_id})
    except AuthServerUnavailable:
        return UNAVAILABLE

    if status == 200 and body.get("sessions_revoked"):
        _clear_pending(user_id)
        logger.info("Sessions revoked for %s", user_id)
        return DONE
    if status == 404:
        _clear_pending(user_id)
        logger.error("Session revocation: user %s not found in authserver", user_id)
        return DONE
    return FAILED


@shared_task(bind=True, max_retries=MAX_RETRIES)
def revoke_all_sessions(self, user_id):
    """Idempotent: revoking already-revoked sessions is a no-op in authserver."""
    if _revoke_once(user_id) == DONE:
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
def retry_pending_session_revocations(now=None):
    """
    Returns how many are still pending after this run, or -1 if a run was
    already in progress.
    """
    if not cache.add(SWEEP_LOCK_KEY, "1", SWEEP_LOCK_TIMEOUT):
        return -1
    try:
        redis = _redis()
        now = int(time.time() if now is None else now)
        batch = [raw.decode() for raw in redis.zrange(QUEUE_KEY, 0, SWEEP_BATCH - 1)]
        for user_id in batch:
            outcome = _revoke_once(user_id)
            if outcome == DONE:
                continue
            # Tried: to the back of the line, so the next sweep reaches others.
            redis.zadd(QUEUE_KEY, {user_id: now}, xx=True)
            since = redis.hget(SINCE_KEY, user_id)
            if since and now - int(since) > ALERT_AFTER_SECONDS:
                logger.error(
                    "Sessions for %s still not revoked %s minutes after a password "
                    "reset; revoke them from the admin console",
                    user_id, (now - int(since)) // 60,
                )
            if outcome == UNAVAILABLE:
                # authserver is down: every remaining call would just wait out
                # its timeout. The next sweep resumes from the members not yet
                # tried, since they are now at the front.
                logger.warning("Session revocation sweep stopped: authserver unavailable")
                break
        return redis.zcard(QUEUE_KEY)
    finally:
        cache.delete(SWEEP_LOCK_KEY)
