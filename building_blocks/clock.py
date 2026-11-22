"""Business time: store UTC, compute business periods in India Standard Time (ADR-053).

Midnight IST is 18:30 UTC the day before, so a "this month" query bounded by UTC
midnights puts the last 5½ hours of each IST month in the wrong one. Every business period
(day, week, month, year) comes from period_bounds; no other code computes one.
"""

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo

BUSINESS_TZ = ZoneInfo("Asia/Kolkata")
PERIODS = ("day", "week", "month", "year")


def now() -> datetime:
    """The current time, as an aware UTC datetime."""
    return datetime.now(timezone.utc)


def _local_date(at: datetime, tz: tzinfo) -> date:
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError(f"{at!r} is naive: pass an aware datetime, such as clock.now().")
    return at.astimezone(tz).date()


def _first_of_next_month(day: date) -> date:
    return date(day.year + 1, 1, 1) if day.month == 12 else date(day.year, day.month + 1, 1)


def period_bounds(kind: str, at: datetime, tz: tzinfo = BUSINESS_TZ) -> tuple[datetime, datetime]:
    """The half-open UTC bounds [start, end) of the day, week, month or year containing ``at``.

    Periods start at midnight in ``tz``; weeks start on Monday.
    """
    day = _local_date(at, tz)
    if kind == "day":
        start, end = day, day + timedelta(days=1)
    elif kind == "week":
        start = day - timedelta(days=day.weekday())
        end = start + timedelta(days=7)
    elif kind == "month":
        start = day.replace(day=1)
        end = _first_of_next_month(start)
    elif kind == "year":
        start, end = date(day.year, 1, 1), date(day.year + 1, 1, 1)
    else:
        raise ValueError(f"Unknown period {kind!r}: use one of {', '.join(PERIODS)}.")
    return tuple(datetime.combine(d, time.min, tzinfo=tz).astimezone(timezone.utc) for d in (start, end))


def period_key(at: datetime) -> str:
    """The IST month containing ``at``, as YYYY-MM."""
    return _local_date(at, BUSINESS_TZ).strftime("%Y-%m")
