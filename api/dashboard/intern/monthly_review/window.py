"""
Monthly review submission window.

The window opens on the last WINDOW_DAYS_BEFORE_MONTH_END days of a month and
stays open for the first WINDOW_DAYS_AFTER_MONTH_END days of the next month.
Every day of the window counts toward the month that is ending:

    Oct 30, Oct 31, Nov 1, Nov 2  ->  review for October

All dates are IST calendar dates — callers pass DateTimeUtils.get_ist_today().
This is the single source of truth for the window; the intern endpoints, the
admin side and the notification cron all go through it.
"""
import calendar
from dataclasses import dataclass, replace
from datetime import date, timedelta

WINDOW_DAYS_BEFORE_MONTH_END = 2  # last 2 days of the month
WINDOW_DAYS_AFTER_MONTH_END = 2   # first 2 days of the next month


@dataclass(frozen=True)
class MonthlyReviewWindow:
    is_open: bool
    year: int          # the month being reviewed
    month: int
    period_start: date
    period_end: date
    opens_on: date     # first day the window is open (inclusive)
    closes_on: date    # last day the window is open (inclusive)

    def to_dict(self) -> dict:
        return {
            "window_open": self.is_open,
            "year": self.year,
            "month": self.month,
            "month_name": calendar.month_name[self.month],
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "opens_on": self.opens_on.isoformat(),
            "closes_on": self.closes_on.isoformat(),
        }


def window_for_month(year: int, month: int) -> MonthlyReviewWindow:
    """The window for reviewing the given month (is_open is always False here)."""
    period_start = date(year, month, 1)
    period_end = date(year, month, calendar.monthrange(year, month)[1])
    return MonthlyReviewWindow(
        is_open=False,
        year=year,
        month=month,
        period_start=period_start,
        period_end=period_end,
        opens_on=period_end - timedelta(days=WINDOW_DAYS_BEFORE_MONTH_END - 1),
        closes_on=period_end + timedelta(days=WINDOW_DAYS_AFTER_MONTH_END),
    )


def get_monthly_review_window(today: date) -> MonthlyReviewWindow:
    """
    Returns the window that is open on `today` (is_open=True), or, when none
    is open, the next one to open (is_open=False) — which is always the one
    for the current month.
    """
    prev_year, prev_month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)

    # Early in a month the previous month's window may still be open; late in
    # a month the current month's window may already be open.
    for year, month in ((prev_year, prev_month), (today.year, today.month)):
        window = window_for_month(year, month)
        if window.opens_on <= today <= window.closes_on:
            return replace(window, is_open=True)

    return window_for_month(today.year, today.month)
