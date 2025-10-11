from datetime import datetime, timedelta

from db.learning_circle import UserCircleLink, LearningCircle


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


def is_learning_circle_member(user_id, circle_id):
    user_circle_link = UserCircleLink.objects.filter(
        user_id=user_id,
        circle_id=circle_id,
        accepted=True
    ).exists()

    if user_circle_link:
        return True
    return False


def is_valid_learning_circle(circle_id):
    learning_circle = LearningCircle.objects.filter(
        id=circle_id
    ).exists()

    if learning_circle:
        return True
    return False
