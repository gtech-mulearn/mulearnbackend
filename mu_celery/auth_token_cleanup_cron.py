"""
Hourly cleanup of expired OAuth tokens in authserver (plan section 13).

authserver owns the oauth2_provider_* tables, so this service never touches
them: it asks authserver's internal API to delete the expired rows. Each call
is capped server-side so it fits inside one web request; when a call reports
more rows left, this task calls again, up to MAX_ROUNDS per run. A large
backlog (the very first run) is therefore cleared over a few hours instead of
in one long request.
"""

import logging

from celery import shared_task
from django.core.cache import cache

from utils.authserver_client import AuthServerUnavailable, call

logger = logging.getLogger(__name__)

MAX_ROUNDS = 10
LIMIT_PER_CALL = 1000

# Same overlap guard as org_aggregates_cron: an atomic Redis SETNX, released in
# `finally`, with a timeout below the hourly interval so a crashed worker
# cannot wedge it.
LOCK_KEY = "auth_token_cleanup_cron_lock"
LOCK_TIMEOUT = 60 * 50


@shared_task
def clear_expired_auth_tokens():
    """
    Returns the total rows deleted, -1 if a run was already in progress, or
    None if authserver could not be reached (the next hourly run retries).
    """
    if not cache.add(LOCK_KEY, "1", LOCK_TIMEOUT):
        return -1
    try:
        return _run()
    finally:
        cache.delete(LOCK_KEY)


def _run():
    total = 0
    for _ in range(MAX_ROUNDS):
        try:
            status, body = call("POST", "maintenance/cleartokens/", json={"limit": LIMIT_PER_CALL})
        except AuthServerUnavailable:
            logger.exception("Auth token cleanup: authserver unavailable")
            return None
        if status != 200:
            logger.error("Auth token cleanup rejected: HTTP %s %s", status, body)
            return None
        total += sum((body.get("deleted") or {}).values())
        if not body.get("more"):
            break
    logger.info("Auth token cleanup deleted %s rows", total)
    return total
