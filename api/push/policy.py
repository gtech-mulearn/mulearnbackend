"""
Pure sending rules: no database, no network. The sender and the engine gather
the facts (preferences, counts, timestamps) and these functions decide.
Tested in api/push/tests/test_policy.py.
"""
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ACTIVITY = "activity"
ENGAGEMENT = "engagement"
CAMPAIGN = "campaign"
TEST = "test"


def zone(name: Optional[str], fallback: str = "Asia/Kolkata") -> ZoneInfo:
    try:
        return ZoneInfo(name or fallback)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo(fallback)


def local_now(now_utc: datetime, tz_name: Optional[str]) -> datetime:
    return now_utc.astimezone(zone(tz_name))


def in_quiet_hours(local: datetime, start: int, end: int) -> bool:
    """Quiet from `start` (inclusive) to `end` (exclusive), in local hours.
    Wraps midnight when start > end (22 → 8). start == end means never."""
    h = local.hour
    if start == end:
        return False
    if start < end:
        return start <= h < end
    return h >= start or h < end


def quiet_ends_at(now_utc: datetime, tz_name: Optional[str], start: int, end: int) -> datetime:
    """UTC time at which the current quiet window ends (now if not quiet)."""
    local = local_now(now_utc, tz_name)
    if not in_quiet_hours(local, start, end):
        return now_utc
    candidate = local.replace(hour=end, minute=0, second=0, microsecond=0)
    if candidate <= local:
        candidate += timedelta(days=1)
    return candidate.astimezone(dt_timezone.utc)


def local_day_start_utc(now_utc: datetime, tz_name: Optional[str]) -> datetime:
    local = local_now(now_utc, tz_name)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.astimezone(dt_timezone.utc)


def nudge_hour(user_id: str, window_start: int, window_end: int) -> int:
    """A stable local hour for this user's nudges inside [start, end).
    Spreads the user base evenly across the window, so each hourly engine
    run handles roughly 1/(end-start) of users."""
    span = max(1, window_end - window_start)
    return window_start + zlib.crc32(user_id.encode()) % span


def fatigue_multiplier(unopened_in_a_row: int, max_multiplier: int) -> int:
    """Each consecutive unopened engagement push doubles the cooldown."""
    return min(2 ** max(0, unopened_in_a_row), max(1, max_multiplier))


@dataclass
class UserFacts:
    """What the sender knows about one recipient at decision time."""

    user_id: str
    push_enabled: bool = True
    engagement_enabled: bool = True
    muted_categories: list = field(default_factory=list)
    quiet_start: int = 22
    quiet_end: int = 8
    timezone: str = "Asia/Kolkata"
    active_devices: int = 0
    sent_today: int = 0
    engagement_sent_today: int = 0


@dataclass
class Decision:
    status: str  # PushDeliveryLog.Status value
    defer_until: Optional[datetime] = None

    @property
    def send(self) -> bool:
        return self.status == "sent"


def decide(
    facts: UserFacts,
    source: str,
    config: dict,
    now_utc: datetime,
    category: Optional[str] = None,
    respect_quiet_hours: bool = True,
    defer_in_quiet_hours: bool = False,
) -> Decision:
    """Whether to send one push to one user now. First failing check wins.
    `sent` means 'go ahead'; the sender writes the final sent/failed."""
    g = config["global"]
    if g.get("kill_switch"):
        return Decision("skipped_disabled")
    if source != TEST:
        if not facts.push_enabled:
            return Decision("skipped_pref")
        if source == ENGAGEMENT and not facts.engagement_enabled:
            return Decision("skipped_pref")
        if category and category in (facts.muted_categories or []):
            return Decision("skipped_pref")
    if facts.active_devices <= 0:
        return Decision("no_device")
    if source != TEST and respect_quiet_hours:
        local = local_now(now_utc, facts.timezone)
        if in_quiet_hours(local, facts.quiet_start, facts.quiet_end):
            if defer_in_quiet_hours:
                return Decision(
                    "deferred",
                    quiet_ends_at(now_utc, facts.timezone, facts.quiet_start, facts.quiet_end),
                )
            return Decision("skipped_quiet")
    if source != TEST:
        if facts.sent_today >= int(g.get("daily_cap", 6)):
            return Decision("skipped_cap")
        if source == ENGAGEMENT and facts.engagement_sent_today >= int(g.get("engagement_daily_cap", 1)):
            return Decision("skipped_cap")
    return Decision("sent")


def truncate(text: str, limit: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
