"""
Push settings: code defaults merged with admin overrides from `push_config`.

Keys:
  global        kill switch, caps, rate, quiet-hour and nudge-window defaults
  rule:<KEY>    one engagement rule (enabled, cooldown, thresholds, copy
                versions; rows saved before versions may hold single copy)
  types         {NOTIFICATION_TYPE: bool} push on/off per activity type

A stored row overrides only the fields it sets. Reads are cached for
CACHE_TTL seconds; writes go through set_config(), which clears the cache
once the write commits.
"""
import copy
import re
import string

from django.core.cache import cache
from django.db import transaction

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
        # Copy versions, rotated per person (engine.pick_variant). The first is
        # the default. Placeholders: RULE_PLACEHOLDERS.
        "variants": [
            {"key": "see_you", "title": "{circle} meets soon",
             "body": "{meeting} starts at {time}. See you there."},
            {"key": "bugs", "title": "{circle} at {time}",
             "body": "Up next: {meeting}. Bring your doubts, we'll bring the bugs."},
            {"key": "seat", "title": "Your seat at {circle} is waiting",
             "body": "{meeting} starts at {time}. Grab a chai and join."},
            {"key": "starts_at", "title": "{time}: {circle}",
             "body": "{meeting} is on. Questions welcome, cameras optional."},
            {"key": "nudge", "title": "{circle} starts in a bit ⏰",
             "body": "{meeting} at {time}. Come say hi."},
        ],
    },
    "EVENT_SOON": {
        "enabled": True,
        "weight": 80,
        "urgent": True,
        "lead_hours": 24,
        "variants": [
            {"key": "coming_up", "title": "{event} is coming up",
             "body": "It starts {when}. You marked it interested."},
            {"key": "interested", "title": 'You said "interested". Here we go.',
             "body": "{event} starts {when}. Charge your laptop before it starts."},
            {"key": "calendar", "title": "{event}, {when}",
             "body": "You're on the interested list. See you there."},
            {"key": "heads_up", "title": "Heads up: {event}",
             "body": "Starts {when}. Bring a friend who'd like it too."},
            {"key": "ready", "title": "Ready for {event}? 🎟️",
             "body": "It kicks off {when}."},
        ],
    },
    "STREAK_RESCUE": {
        "enabled": True,
        "weight": 70,
        "urgent": False,
        "min_streak_days": 2,
        "local_hour_start": 18,
        "local_hour_end": 20,
        "cooldown_hours": 24,
        "variants": [
            {"key": "keep", "title": "Keep your {days}-day streak",
             "body": "One task today keeps it going."},
            {"key": "ctrl_s", "title": "Ctrl + S your streak 💾",
             "body": "{days} days saved so far. Today's task makes it {days_plus_one}."},
            {"key": "not_found", "title": "404: today's task not found",
             "body": "Find one in 10 minutes and keep your {days}-day streak alive."},
            {"key": "commit", "title": "git commit to day {days_plus_one}",
             "body": "{days} days in a row. One task today, no force-push needed."},
            {"key": "strong", "title": "{days} days strong",
             "body": "Don't let today break it. One small task is enough."},
        ],
    },
    "COMEBACK": {
        "enabled": True,
        "weight": 50,
        "urgent": False,
        "tiers_days": [3, 7, 14, 30],
        # body when there are new tasks, body_no_tasks when there are none.
        "variants": [
            {"key": "kept_going", "title": "Your interest groups kept going",
             "body": "{count} new tasks since you left. Pick one up.",
             "body_no_tasks": "It's been {days} days. Your next task is waiting."},
            {"key": "missed_you", "title": "Your groups missed you. Mostly.",
             "body": "{count} new tasks dropped while you were away. Start with a short one.",
             "body_no_tasks": "{days} days away. A 10-minute task is a good way back."},
            {"key": "door_open", "title": "The door's still open 👋",
             "body": "{count} new tasks are waiting. Pick the easiest one.",
             "body_no_tasks": "It's been {days} days. Start small, one task."},
            {"key": "new_stuff", "title": "New tasks since you've been gone",
             "body": "{count} of them. One is probably just your thing.",
             "body_no_tasks": "{days} days since your last visit. Come see what's new."},
            {"key": "restart", "title": "Restart, not from scratch",
             "body": "Your karma's still here, plus {count} new tasks to try.",
             "body_no_tasks": "Your karma's still here after {days} days. Pick up a task."},
        ],
    },
}

# Placeholders each rule's copy may use (the engine supplies exactly these).
RULE_PLACEHOLDERS = {
    "MEETING_SOON": {"circle", "meeting", "time"},
    "EVENT_SOON": {"event", "when"},
    "STREAK_RESCUE": {"days", "days_plus_one"},
    "COMEBACK": {"count", "days"},
}
NO_TASKS_PLACEHOLDERS = {"days"}

# Single-copy keys stored before versions existed. A rule row that still has
# any of them is sent as one "legacy" version (rule_variants).
LEGACY_COPY_KEYS = ("title", "body", "body_with_tasks", "body_default")
# Version field <- the old key it came from, per rule.
_LEGACY_FIELDS = {"title": "title", "body": "body", "body_no_tasks": None}
_LEGACY_FIELDS_COMEBACK = {"title": "title", "body": "body_with_tasks", "body_no_tasks": "body_default"}

VARIANT_KEY_RE = re.compile(r"^[a-z0-9_]{1,16}$")
MAX_VARIANTS = 10
MAX_TITLE = 40
MAX_BODY = 100
VARIANT_FIELDS = {"key", "title", "body", "body_no_tasks", "voice"}


def _legacy_fields(rule_key: str) -> dict:
    return _LEGACY_FIELDS_COMEBACK if rule_key == "COMEBACK" else _LEGACY_FIELDS


def legacy_copy_keys(rule_key: str) -> set:
    """The old single-copy keys this rule had (a subset of LEGACY_COPY_KEYS)."""
    return {k for k in _legacy_fields(rule_key).values() if k}


def rule_variants(rule_key: str, rule_cfg: dict) -> list:
    """The copy versions to rotate for one rule. A row that still has old
    single-copy keys becomes one "legacy" version; each field falls back to
    the first default version, so a title-only override keeps a real body."""
    if any(k in rule_cfg for k in LEGACY_COPY_KEYS):
        first = DEFAULT_RULES[rule_key]["variants"][0]
        legacy = {"key": "legacy"}
        for name, old_key in _legacy_fields(rule_key).items():
            value = rule_cfg.get(old_key) if old_key else None
            legacy[name] = value if isinstance(value, str) and value.strip() else first.get(name)
        return [legacy]
    return rule_cfg["variants"]


def _text_error(where: str, value, limit: int):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return f"{where} must be text of 1 to {limit} characters."
    return None


def _placeholder_error(where: str, template: str, allowed: set):
    try:
        fields = list(string.Formatter().parse(template))
    except ValueError:
        return f"{where} has a stray {{ or }}. Write {{{{ or }}}} for a literal brace."
    for _, name, spec, conversion in fields:
        if name is None:
            continue
        if name not in allowed:
            names = ", ".join(f"{{{p}}}" for p in sorted(allowed))
            return f"{where} uses {{{name}}}, which this rule doesn't have. It can use {names}."
        if spec or conversion:
            return f"{where}: write {{{name}}} with nothing after the name."
    return None


def validate_variants(rule_key: str, variants: object):
    """An error message for one rule's versions, or None when they are valid."""
    allowed = RULE_PLACEHOLDERS.get(rule_key)
    if allowed is None:
        return f"Unknown rule: {rule_key}."
    if not isinstance(variants, list) or not 1 <= len(variants) <= MAX_VARIANTS:
        return f"{rule_key} needs a list of 1 to {MAX_VARIANTS} versions."
    seen = set()
    for i, v in enumerate(variants, 1):
        if not isinstance(v, dict):
            return f"{rule_key} version {i} must be an object."
        key = v.get("key")
        if not isinstance(key, str) or not VARIANT_KEY_RE.fullmatch(key):
            return (f"{rule_key} version {i}: the key must be 1 to 16 lowercase letters, "
                    "digits or underscores.")
        if key in seen:
            return f"{rule_key} has two versions with the key {key}."
        seen.add(key)
        where = f"{rule_key}.{key}"
        unknown = sorted(set(v) - VARIANT_FIELDS)
        if unknown:
            return f"{where} has an unknown field: {unknown[0]}."
        checks = [("title", MAX_TITLE, allowed), ("body", MAX_BODY, allowed)]
        if rule_key == "COMEBACK":
            checks.append(("body_no_tasks", MAX_BODY, NO_TASKS_PLACEHOLDERS))
        elif v.get("body_no_tasks") is not None:
            return f"{where}: body_no_tasks is only for COMEBACK."
        for name, limit, names in checks:
            error = (_text_error(f"{where} {name}", v.get(name), limit)
                     or _placeholder_error(f"{where} {name}", v[name], names))
            if error:
                return error
        if v.get("voice") is not None and not isinstance(v["voice"], str):
            return f"{where} voice must be text."
    return None

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
    # Clear only once the change is committed: clearing inside the open
    # transaction lets a concurrent reader re-cache the old values for
    # CACHE_TTL, and a rolled-back change has nothing to clear.
    transaction.on_commit(_clear_cache)


def _clear_cache() -> None:
    try:
        cache.delete(CACHE_KEY)
    except Exception:
        pass
