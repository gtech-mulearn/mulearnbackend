"""
Partner call budgets and per-subject locks (spec B §3.7).

Only cache.add/incr/get/delete are used, so this works on Redis in production
and on LocMem in tests. The partner's limit is per KEY, shared by every
µLearn user, hence one counter across all servers.
"""
import time
import uuid
from contextlib import contextmanager

from django.core.cache import cache

from .errors import PartnerError


def _now():
    return int(time.time())


def _count(key, ttl):
    return 1 if cache.add(key, 1, ttl) else cache.incr(key)


def take_partner_call(provider, limit_per_minute):
    """Reserve one outbound call. Returns None, or seconds until the next minute."""
    now = _now()
    minute = now // 60
    if _count(f"partner:{provider}:rpm:{minute}", 70) > limit_per_minute:
        return (minute + 1) * 60 - now
    return None


def take_actor_attempt(provider, actor_id, limit=10, window=600):
    """At most `limit` authorize/sign-in calls per person per window."""
    now = _now()
    bucket = now // window
    if _count(f"partner:{provider}:actor:{actor_id}:{bucket}", window + 10) > limit:
        return (bucket + 1) * window - now
    return None


@contextmanager
def link_lock(provider, subject_key, timeout=30):
    key = f"partner:{provider}:lock:{subject_key}"
    token = uuid.uuid4().hex
    if not cache.add(key, token, timeout):
        raise PartnerError("in_progress")
    try:
        yield
    finally:
        if cache.get(key) == token:
            cache.delete(key)
