from datetime import datetime, timedelta


def get_today_start_end(date_time):
    start_of_day = datetime(
        date_time.year,
        date_time.month,
        date_time.day,
        0,
        0,
        0
    )
    end_of_day = datetime(
        date_time.year,
        date_time.month,
        date_time.day,
        23,
        59,
        59
    ) + timedelta(seconds=1)

    return start_of_day, end_of_day


def get_week_start_end(date_time):
    monday = date_time.weekday()

    start_of_week = date_time - timedelta(days=monday)

    start_of_week = start_of_week.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    end_of_week = start_of_week + timedelta(
        days=6,
        hours=23,
        minutes=59,
        seconds=59
    )
    return start_of_week, end_of_week

