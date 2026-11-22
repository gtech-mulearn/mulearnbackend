from datetime import datetime, timedelta, timezone

import pytest

from building_blocks.clock import BUSINESS_TZ, now, period_bounds, period_key


def utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


def test_now_is_an_aware_utc_datetime():
    value = now()

    assert value.utcoffset() == timedelta(0)
    assert abs(datetime.now(timezone.utc) - value) < timedelta(seconds=5)


def test_the_business_time_zone_is_india_standard_time():
    assert str(BUSINESS_TZ) == "Asia/Kolkata"
    assert BUSINESS_TZ.utcoffset(utc(2026, 1, 1)) == timedelta(hours=5, minutes=30)


def test_18_29_utc_on_31_january_is_still_january_ist():
    assert period_key(utc(2026, 1, 31, 18, 29, 59)) == "2026-01"


def test_18_30_utc_on_31_january_is_february_ist():
    assert period_key(utc(2026, 1, 31, 18, 30)) == "2026-02"


def test_the_month_bounds_are_ist_midnights_in_utc():
    assert period_bounds("month", utc(2026, 1, 31, 18, 30)) == (utc(2026, 1, 31, 18, 30), utc(2026, 2, 28, 18, 30))
    assert period_bounds("month", utc(2026, 1, 31, 18, 29)) == (utc(2025, 12, 31, 18, 30), utc(2026, 1, 31, 18, 30))


def test_december_rolls_into_january_of_the_next_year():
    assert period_key(utc(2026, 12, 31, 18, 30)) == "2027-01"
    assert period_bounds("month", utc(2026, 12, 15)) == (utc(2026, 11, 30, 18, 30), utc(2026, 12, 31, 18, 30))
    assert period_bounds("year", utc(2026, 12, 31, 18, 29)) == (utc(2025, 12, 31, 18, 30), utc(2026, 12, 31, 18, 30))
    assert period_bounds("year", utc(2026, 12, 31, 18, 30)) == (utc(2026, 12, 31, 18, 30), utc(2027, 12, 31, 18, 30))


def test_weeks_start_on_monday_at_midnight_ist():
    # Wednesday 18 November 2026, 15:30 IST.
    start, end = period_bounds("week", utc(2026, 11, 18, 10, 0))

    assert start == utc(2026, 11, 15, 18, 30)
    assert start.astimezone(BUSINESS_TZ).weekday() == 0
    assert start.astimezone(BUSINESS_TZ).time().isoformat() == "00:00:00"
    assert end == start + timedelta(days=7)


def test_sunday_18_30_utc_is_already_the_next_week():
    # Monday 23 November 2026, 00:00 IST.
    assert period_bounds("week", utc(2026, 11, 22, 18, 30))[0] == utc(2026, 11, 22, 18, 30)
    assert period_bounds("week", utc(2026, 11, 22, 18, 29))[0] == utc(2026, 11, 15, 18, 30)


def test_day_bounds_run_from_ist_midnight_to_the_next():
    assert period_bounds("day", utc(2026, 3, 1, 18, 29)) == (utc(2026, 2, 28, 18, 30), utc(2026, 3, 1, 18, 30))


@pytest.mark.parametrize("kind", ["day", "week", "month", "year"])
def test_bounds_are_half_open_and_back_to_back(kind):
    start, end = period_bounds(kind, utc(2026, 6, 10, 12, 0))

    assert start <= utc(2026, 6, 10, 12, 0) < end
    assert period_bounds(kind, end)[0] == end
    assert period_bounds(kind, end - timedelta(microseconds=1)) == (start, end)
    assert start.tzinfo == end.tzinfo == timezone.utc


def test_an_aware_datetime_in_another_zone_gives_the_same_bounds():
    ist = utc(2026, 1, 31, 18, 30).astimezone(BUSINESS_TZ)

    assert period_bounds("month", ist) == period_bounds("month", utc(2026, 1, 31, 18, 30))
    assert period_key(ist) == "2026-02"


def test_another_time_zone_can_be_passed():
    assert period_bounds("day", utc(2026, 1, 1, 5), tz=timezone.utc) == (utc(2026, 1, 1), utc(2026, 1, 2))


def test_a_naive_datetime_raises():
    with pytest.raises(ValueError, match="naive"):
        period_bounds("month", datetime(2026, 1, 31, 18, 30))
    with pytest.raises(ValueError, match="naive"):
        period_key(datetime(2026, 1, 31, 18, 30))


def test_an_unknown_period_raises():
    with pytest.raises(ValueError, match="quarter"):
        period_bounds("quarter", utc(2026, 1, 1))
