"""
Push settings: code defaults merged with admin overrides from `push_config`.

Keys:
  global        kill switch, caps, rate, quiet-hour and nudge-window defaults
  rule:<KEY>    one engagement rule (enabled, cooldown, thresholds, copy)
  types         {NOTIFICATION_TYPE: bool} push on/off per activity type

A stored row overrides only the fields it sets. Reads are cached for
CACHE_TTL seconds; writes go through set_config(), which clears the cache.
"""
import copy

from django.core.cache import cache

CACHE_KEY = "push:config:v1"
CACHE_TTL = 60

DEFAULT_GLOBAL = {
    "kill_switch": False,
    # Per user per local day, across every source.
    "daily_cap": 6,
    # Engagement nudges per user per local day.
    "engagement_daily_cap": 1,
    # Global FCM send budget (messages per minute), shared by all workers.
    "max_per_minute": 6000,
    "default_quiet_start": 22,
    "default_quiet_end": 8,
    "default_timezone": "Asia/Kolkata",
    # Local hours in which non-urgent nudges may be sent.
    "nudge_window_start": 10,
    "nudge_window_end": 20,
    # Fatigue: each unopened engagement push in this many days doubles the
    # rule cooldown, up to max_backoff_days.
    "fatigue_lookback_days": 14,
    "max_backoff_days": 14,
    # Users per engagement / campaign chunk task.
    "chunk_size": 1000,
}

DEFAULT_RULES = {
    "MEETING_SOON": {
        "enabled": True,
        "weight": 100,
        "urgent": True,
        "lead_minutes_min": 60,
        "lead_minutes_max": 120,
        "title": "{circle} meets soon",
        "body": "{meeting} starts at {time}. See you there.",
    },
    "EVENT_SOON": {
        "enabled": True,
        "weight": 80,
        "urgent": True,
        "lead_hours": 24,
        "title": "{event} is coming up",
        "body": "It starts {when}. You marked it interested.",
    },
    "STREAK_RESCUE": {
        "enabled": True,
        "weight": 70,
        "urgent": False,
        "min_streak_days": 2,
        "local_hour_start": 18,
        "local_hour_end": 20,
        "cooldown_hours": 24,
        "title": "Keep your {days}-day streak",
        "body": "One task today keeps it going.",
    },
    "COMEBACK": {
        "enabled": True,
        "weight": 50,
        "urgent": False,
        "tiers_days": [3, 7, 14, 30],
        "title": "Your interest groups kept going",
        "body_with_tasks": "{count} new tasks since you left. Pick one up.",
        "body_default": "Your next task is waiting. Come back and earn karma.",
    },
}

# Activity types that are eligible for push but stay off unless an admin turns
# them on: announcements that reach very large audiences, and admin queues
# that are better read in the dashboard.
DEFAULT_TYPES_OFF = {
    "EVENT_PUBLISHED",
    "OFFICE_HOURS_ANNOUNCED",
    "SALT_MANGO_TREE_ANNOUNCED",
    "INSPIRATION_STATION_ANNOUNCED",
    "GRAB_YOUR_SUPERPOWERS_ANNOUNCED",
    "ADMIN_EVENT_PENDING",
    "ADMIN_COMPANY_PENDING",
    "JOB_PENDING_APPROVAL",
}


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _load_rows() -> dict:
    from db.push import PushConfig

    return {row.key: row.value for row in PushConfig.objects.all()}


def get_config() -> dict:
    """{'global': {...}, 'rules': {KEY: {...}}, 'types': {TYPE: bool}}"""
    try:
        cached = cache.get(CACHE_KEY)
    except Exception:
        cached = None
    if cached is not None:
        return cached
    rows = _load_rows()
    config = build_config(rows)
    try:
        cache.set(CACHE_KEY, config, CACHE_TTL)
    except Exception:
        pass
    return config


def build_config(rows: dict) -> dict:
    """Pure: merge stored rows over the defaults."""
    rules = {
        key: _merge(default, rows.get(f"rule:{key}", {}))
        for key, default in DEFAULT_RULES.items()
    }
    return {
        "global": _merge(DEFAULT_GLOBAL, rows.get("global", {})),
        "rules": rules,
        "types": dict(rows.get("types", {})),
    }


def push_allowed_for_type(config: dict, notif_type: str, eligible: list) -> bool:
    """An activity type pushes when its TypeMeta allows PUSH and it is on:
    an admin override wins, otherwise DEFAULT_TYPES_OFF decides."""
    if "PUSH" not in (eligible or []):
        return False
    override = config.get("types", {}).get(notif_type)
    if override is not None:
        return bool(override)
    return notif_type not in DEFAULT_TYPES_OFF


ALLOWED_GLOBAL_KEYS = set(DEFAULT_GLOBAL)


def set_config(key: str, value: dict, user_id: str) -> None:
    from db.push import PushConfig

    PushConfig.objects.update_or_create(
        key=key, defaults={"value": value, "updated_by_id": user_id}
    )
    try:
        cache.delete(CACHE_KEY)
    except Exception:
        pass
