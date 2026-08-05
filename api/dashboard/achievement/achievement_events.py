"""
Achievement Event Producer

Emits normalized events for the achievement system.
All events are immutable and append-only.

Usage:
    from api.dashboard.achievement.achievement_events import emit_task_completed
    emit_task_completed(user_id="...", task_id="...", ig_id="...", karma=50)
"""
import uuid
from datetime import datetime, date
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class EventType:
    """Canonical event types for the achievement system"""
    TASK_COMPLETED = "task.completed"
    KARMA_AWARDED = "karma.awarded"
    USER_LOGIN = "user.login"
    DISCORD_ACTIVITY = "discord.activity"
    EVENT_ATTENDED = "event.attended"
    LC_MEETING_ATTENDED = "lc.meeting.attended"
    STREAK_MILESTONE = "streak.milestone"


class AchievementEventProducer:
    """
    Produces achievement events with exactly-once semantics.
    Events are persisted to DB then queued for async processing.
    """

    @staticmethod
    def emit(
        event_type: str,
        user_id: str,
        metadata: dict,
        region: str = None,
        event_id: str = None,
    ) -> str:
        """
        Emit an achievement event.

        Args:
            event_type: Type of event (use EventType constants)
            user_id: User who triggered the event
            metadata: Event-specific data (task_id, ig_id, karma, etc.)
            region: Optional region for partitioning
            event_id: Optional idempotency key (auto-generated if not provided)

        Returns:
            event_id for tracking
        """
        from db.achievement import AchievementEvent
        from mu_celery.achievement_tasks import process_achievement_event

        if event_id is None:
            event_id = str(uuid.uuid4())

        try:
            with transaction.atomic():
                event = AchievementEvent.objects.create(
                    id=str(uuid.uuid4()),
                    event_id=event_id,
                    event_type=event_type,
                    user_id=user_id,
                    region=region,
                    metadata=metadata,
                    processed=False,
                    created_at=datetime.now(),
                )

                # Queue for async processing
                process_achievement_event.delay(str(event.id))

                logger.info(
                    f"Achievement event emitted: {event_type} for user {user_id}"
                )
                return event_id

        except Exception as e:
            # If duplicate event_id, silently ignore (idempotent)
            if "Duplicate entry" in str(e) or "uk_event_id" in str(e):
                logger.debug(f"Duplicate event ignored: {event_id}")
                return event_id
            logger.exception(f"Error emitting event: {e}")
            raise


# ============================================================================
# Convenience functions for common events
# ============================================================================


def emit_task_completed(
    user_id: str,
    task_id: str,
    ig_id: str = None,
    karma: int = 0,
    skill_ids: list = None,
) -> str:
    """
    Emit event when a task is completed.

    Args:
        user_id: User who completed the task
        task_id: ID of the completed task
        ig_id: Interest Group ID (if task belongs to an IG)
        karma: Karma points awarded
        skill_ids: List of skill IDs related to this task
    """
    return AchievementEventProducer.emit(
        event_type=EventType.TASK_COMPLETED,
        user_id=user_id,
        metadata={
            "task_id": task_id,
            "ig_id": ig_id,
            "karma": karma,
            "skill_ids": skill_ids or [],
        },
        event_id=f"task_{task_id}_{user_id}",  # Idempotency key
    )


def emit_karma_awarded(
    user_id: str,
    karma: int,
    source: str,
    ig_id: str = None,
    task_id: str = None,
) -> str:
    """
    Emit event when karma is awarded.

    Args:
        user_id: User receiving karma
        karma: Amount of karma awarded
        source: Source of karma (task, referral, bonus, etc.)
        ig_id: Interest Group ID if applicable
        task_id: Task ID if karma is from a task
    """
    return AchievementEventProducer.emit(
        event_type=EventType.KARMA_AWARDED,
        user_id=user_id,
        metadata={
            "karma": karma,
            "source": source,
            "ig_id": ig_id,
            "task_id": task_id,
        },
    )


def emit_user_login(user_id: str) -> str:
    """
    Emit event when user logs in (once per day for streak tracking).

    Args:
        user_id: User who logged in
    """
    today = date.today()
    return AchievementEventProducer.emit(
        event_type=EventType.USER_LOGIN,
        user_id=user_id,
        metadata={"date": str(today)},
        event_id=f"login_{user_id}_{today}",  # Once per day
    )


def emit_event_attended(
    user_id: str,
    event_name: str,
    event_id: str = None,
) -> str:
    """
    Emit event when user attends an event.

    Args:
        user_id: User who attended
        event_name: Name of the event
        event_id: Event ID for deduplication
    """
    return AchievementEventProducer.emit(
        event_type=EventType.EVENT_ATTENDED,
        user_id=user_id,
        metadata={"event_name": event_name},
        event_id=f"event_{event_id}_{user_id}" if event_id else None,
    )


def emit_lc_meeting_attended(
    user_id: str,
    circle_id: str,
    meeting_id: str,
) -> str:
    """
    Emit event when user attends a Learning Circle meeting.

    Args:
        user_id: User who attended
        circle_id: Learning Circle ID
        meeting_id: Meeting ID
    """
    return AchievementEventProducer.emit(
        event_type=EventType.LC_MEETING_ATTENDED,
        user_id=user_id,
        metadata={
            "circle_id": circle_id,
            "meeting_id": meeting_id,
        },
        event_id=f"lc_{meeting_id}_{user_id}",  # Idempotency
    )


def emit_streak_milestone(
    user_id: str,
    streak_type: str,
    streak_count: int,
) -> str:
    """
    Emit event when user reaches a streak milestone.

    Args:
        user_id: User who reached the milestone
        streak_type: Type of streak (daily_task, daily_login)
        streak_count: Number of days in streak
    """
    return AchievementEventProducer.emit(
        event_type=EventType.STREAK_MILESTONE,
        user_id=user_id,
        metadata={
            "streak_type": streak_type,
            "streak_count": streak_count,
        },
        event_id=f"streak_{user_id}_{streak_type}_{streak_count}",
    )
