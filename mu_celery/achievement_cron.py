"""
Achievement Cron Tasks

For correctness, not primary logic:
- Daily streak evaluation
- Missed event backfill
- Data integrity checks

Schedule these via Celery Beat in settings.py
"""
import uuid
from datetime import datetime, date, timedelta
from celery import shared_task
from django.db import models
import logging

logger = logging.getLogger(__name__)


@shared_task
def evaluate_daily_streaks():
    """
    Daily cron: Update all user streaks based on yesterday's activity.
    Run at 00:05 UTC daily.
    """
    from db.achievement import UserDailyActivity, UserStreak

    yesterday = date.today() - timedelta(days=1)

    # Get all users who had activity yesterday
    active_users = list(
        UserDailyActivity.objects.filter(activity_date=yesterday).values_list(
            "user_id", flat=True
        )
    )

    # Get all users with existing streaks
    all_streak_users = list(
        UserStreak.objects.values_list("user_id", flat=True).distinct()
    )

    # Process active users - increment streak
    for user_id in active_users:
        _update_streak(user_id, yesterday, active=True)

    # Process inactive users - reset streak
    inactive_users = set(all_streak_users) - set(active_users)
    for user_id in inactive_users:
        _update_streak(user_id, yesterday, active=False)

    logger.info(
        f"Streak evaluation complete. Active: {len(active_users)}, Reset: {len(inactive_users)}"
    )
    return {"active": len(active_users), "reset": len(inactive_users)}


def _update_streak(user_id: str, activity_date: date, active: bool):
    """Update user streak based on activity"""
    from db.achievement import UserStreak

    streak_types = ["daily_task", "daily_login"]

    for streak_type in streak_types:
        streak, created = UserStreak.objects.get_or_create(
            user_id=user_id,
            streak_type=streak_type,
            defaults={
                "id": str(uuid.uuid4()),
                "current_streak": 0,
                "longest_streak": 0,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )

        if active:
            # Check if streak continues (last_active was yesterday)
            if streak.last_active == activity_date - timedelta(days=1):
                streak.current_streak += 1
            elif streak.last_active != activity_date:
                # New streak or gap - start at 1
                streak.current_streak = 1

            streak.last_active = activity_date
            streak.longest_streak = max(streak.longest_streak, streak.current_streak)
        else:
            # No activity - check if streak should reset
            if streak.last_active and streak.last_active < activity_date:
                streak.current_streak = 0

        streak.updated_at = datetime.now()
        streak.save()

        # Trigger achievement event for streak milestones
        if active and streak.current_streak in [7, 30, 60, 100, 365]:
            from api.dashboard.achievement.achievement_events import (
                emit_streak_milestone,
            )

            emit_streak_milestone(
                user_id=user_id,
                streak_type=streak_type,
                streak_count=streak.current_streak,
            )


@shared_task
def backfill_missing_aggregates():
    """
    Weekly cron: Scan for missing aggregates and backfill.
    Run on Sundays at 02:00 UTC.
    """
    from db.task import KarmaActivityLog
    from db.achievement import UserIgKarma

    # Get all karma logs with IG
    karma_logs = (
        KarmaActivityLog.objects.filter(appraiser_approved=True, task__ig__isnull=False)
        .values("user_id", "task__ig_id")
        .annotate(total_karma=models.Sum("karma"), task_count=models.Count("id"))
    )

    fixed = 0
    for log in karma_logs:
        ig_karma, created = UserIgKarma.objects.get_or_create(
            user_id=log["user_id"],
            ig_id=log["task__ig_id"],
            defaults={
                "id": str(uuid.uuid4()),
                "total_karma": log["total_karma"],
                "task_count": log["task_count"],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )

        if not created:
            # Check and fix discrepancies
            if ig_karma.total_karma != log["total_karma"]:
                ig_karma.total_karma = log["total_karma"]
                ig_karma.task_count = log["task_count"]
                ig_karma.save()
                fixed += 1

    logger.info(f"Backfill complete. Fixed {fixed} discrepancies.")
    return {"fixed": fixed}


@shared_task
def integrity_check():
    """
    Daily cron: Check data integrity.
    Run at 03:00 UTC daily.
    """
    from db.achievement import UserAchievementsLog, AchievementAuditLog

    issues = []

    # Check for achievements without audit logs
    achievements_without_audit = (
        UserAchievementsLog.objects.exclude(
            achievement_id__in=AchievementAuditLog.objects.filter(
                action="issued"
            ).values("achievement_id")
        ).count()
    )

    if achievements_without_audit > 0:
        issues.append(
            f"Found {achievements_without_audit} achievements without audit logs"
        )

    # Check for duplicate user achievements (should not exist with unique constraint)
    from django.db.models import Count

    duplicates = (
        UserAchievementsLog.objects.values("user_id", "achievement_id")
        .annotate(count=Count("id"))
        .filter(count__gt=1)
    )

    if duplicates.exists():
        issues.append(f"Found {duplicates.count()} duplicate achievements")

    if issues:
        logger.warning(f"Integrity issues found: {issues}")
    else:
        logger.info("Integrity check passed")

    return {"issues": issues}


# ============================================================================
# Celery Beat Schedule Configuration
# Add this to your Celery app configuration in settings.py or celery.py
# ============================================================================
"""
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'evaluate-daily-streaks': {
        'task': 'mu_celery.achievement_cron.evaluate_daily_streaks',
        'schedule': crontab(hour=0, minute=5),  # 00:05 UTC daily
    },
    'backfill-aggregates': {
        'task': 'mu_celery.achievement_cron.backfill_missing_aggregates',
        'schedule': crontab(hour=2, minute=0, day_of_week=0),  # Sundays 02:00 UTC
    },
    'integrity-check': {
        'task': 'mu_celery.achievement_cron.integrity_check',
        'schedule': crontab(hour=3, minute=0),  # 03:00 UTC daily
    },
}
"""
