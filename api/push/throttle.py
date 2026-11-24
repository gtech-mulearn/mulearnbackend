"""
Global push send budget, shared by every Celery worker through the Redis
cache: a fixed one-minute window counter. A chunk that would overrun the
budget is not sent; its task reschedules itself for the next window, so a big
campaign spreads out instead of hammering FCM, Redis and the database.
"""
import time

from django.core.cache import cache


def _window_key(now: float) -> str:
    return f"push:rate:{int(now // 60)}"


def reserve(count: int, per_minute: int, now: float = None) -> int:
    """Try to reserve `count` sends in the current minute.
    Returns 0 when reserved, else the seconds to wait before retrying."""
    if count <= 0:
        return 0
    now = time.time() if now is None else now
    key = _window_key(now)
    try:
        cache.add(key, 0, timeout=120)
        used = cache.incr(key, count)
    except Exception:
        # Redis down: send anyway rather than stall every push; FCM's own
        # quota still protects the provider.
        return 0
    if used > per_minute:
        try:
            cache.decr(key, count)
        except Exception:
            pass
        return max(1, 60 - int(now % 60))
    return 0
