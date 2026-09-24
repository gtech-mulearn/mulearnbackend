"""
Retry "sign this member out everywhere" until authserver confirms it.

Used when a password was set but authserver reported the session revocation as
incomplete. The reset link is already consumed by then (it must never be able
to set a second password), so the retry has to happen here rather than by the
person resubmitting the link.
"""

import logging

from celery import shared_task

from utils.authserver_client import AuthServerUnavailable, call

logger = logging.getLogger(__name__)

# 1, 2, 4, 8, 15, 15, 15, 15 minutes: a little over an hour in total.
MAX_RETRIES = 8
MAX_DELAY_SECONDS = 15 * 60


@shared_task(bind=True, max_retries=MAX_RETRIES)
def revoke_all_sessions(self, user_id):
    """
    Idempotent: revoking already-revoked sessions is a no-op in authserver.
    Returns True once confirmed, False if it gave up or the user is gone.
    """
    try:
        status, body = call("POST", "sessions/revoke/", json={"user_id": user_id})
    except AuthServerUnavailable:
        status, body = None, {}

    if status == 200 and body.get("sessions_revoked"):
        logger.info("Sessions revoked for %s after a password reset", user_id)
        return True
    if status == 404:
        logger.error("Session revocation: user %s not found in authserver", user_id)
        return False

    try:
        raise self.retry(countdown=min(60 * 2 ** self.request.retries, MAX_DELAY_SECONDS))
    except self.MaxRetriesExceededError:
        logger.error(
            "Session revocation for %s still incomplete after %s retries; "
            "an admin must sign this member out manually", user_id, MAX_RETRIES,
        )
        return False
