import logging

from django.conf import settings
from django.core.cache import cache

from db.notification import Notification
from utils.utils import DateTimeUtils

logger = logging.getLogger(__name__)

# ── unread-count cache-aside ────────────────────────────────────────────────
# Bounded key space (one key per user, same pattern as the existing
# db_user_{id} cache in register_views.py) — safe to cache per CLAUDE.md's
# "never cache an unbounded key space" rule.
_UNREAD_COUNT_CACHE_KEY = "notif:unread:{user_id}"


def get_unread_count(user_id: str) -> int:
    """
    Cache-aside read for the unread notification badge. Falls back to the
    indexed COUNT query (idx_notification_user_unread) on a cache miss and
    repopulates the cache — never trusts a stale value beyond the TTL.

    Redis being unreachable degrades to "always compute from the DB" rather
    than raising — a cache outage must never take an otherwise-successful
    read down with it.
    """
    key = _UNREAD_COUNT_CACHE_KEY.format(user_id=user_id)
    try:
        count = cache.get(key)
    except Exception:
        logger.warning("get_unread_count: cache.get failed for user=%s, falling back to DB", user_id, exc_info=True)
        count = None

    if count is None:
        count = Notification.objects.filter(
            user_id=user_id, is_read=False, is_archived=False
        ).count()
        try:
            cache.set(key, count, settings.NOTIFICATION_UNREAD_COUNT_CACHE_TTL)
        except Exception:
            logger.warning("get_unread_count: cache.set failed for user=%s", user_id, exc_info=True)
    return count


def invalidate_unread_count(user_id: str) -> None:
    """
    Call after any write that changes a user's unread set: a new notification
    landing, a read/archive/delete mutation. Cache-aside, not cache-and-hope —
    every write path that can change the count must call this.

    Must never raise: this runs inside dispatch()'s on_commit callback, after
    the business transaction (join/approve/remove/etc.) has already committed
    successfully — a Redis outage here must not turn an otherwise-successful
    request into a 500. Worst case on failure is a stale badge for up to
    NOTIFICATION_UNREAD_COUNT_CACHE_TTL seconds, which is an acceptable
    degradation for a cache-aside key.
    """
    try:
        cache.delete(_UNREAD_COUNT_CACHE_KEY.format(user_id=user_id))
    except Exception:
        logger.warning("invalidate_unread_count: cache.delete failed for user=%s", user_id, exc_info=True)


class NotificationUtils:
    """
    Utility class for Notification
    """

    @staticmethod
    def insert_notification(user, title, description, button, url, created_by):
        """
        Insert notification

        Args:
            user_id:
            title:
            description:
            button:
            url:
            created_by:

        Returns:
            True if the notification is inserted successfully, False otherwise.
        """

        Notification.objects.create(user=user, title=title, description=description, button=button, url=url,
                                    created_at=DateTimeUtils.get_current_utc_time(), created_by=created_by)
        return True
