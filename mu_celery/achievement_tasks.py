"""
Achievement Celery Tasks

Handles:
1. Async event processing → Updates aggregates (NOT auto-issue)
2. Claim processing → Idempotent issuance + VC generation

All operations are idempotent.
"""
import uuid
from datetime import datetime, date
from celery import shared_task
from django.db import transaction, IntegrityError
from django.conf import settings
import requests
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_achievement_event(self, event_id: str):
    """
    Process an achievement event - UPDATE AGGREGATES ONLY.

    This does NOT auto-issue achievements. Users must claim eligible achievements.

    1. Load event
    2. Update aggregates (IG karma, skill progress, daily activity)
    3. Mark event as processed
    """
    from db.achievement import AchievementEvent

    try:
        event = AchievementEvent.objects.get(id=event_id)

        if event.processed:
            return {"status": "already_processed", "event_id": event_id}

        # Update aggregates based on event type
        _update_aggregates(event)

        # Mark event as processed
        event.processed = True
        event.save()

        logger.info(f"Event processed: {event.event_type} for user {event.user_id}")

        return {
            "status": "success",
            "event_id": event_id,
            "message": "Aggregates updated. User can now claim eligible achievements.",
        }

    except AchievementEvent.DoesNotExist:
        logger.error(f"Event not found: {event_id}")
        return {"status": "error", "message": "Event not found"}
    except Exception as e:
        logger.exception(f"Error processing event {event_id}: {e}")
        raise self.retry(exc=e)


def _update_aggregates(event):
    """Update pre-aggregated tables based on event"""
    from db.achievement import UserIgKarma, UserSkillProgress, UserDailyActivity

    user_id = str(event.user_id)
    metadata = event.metadata
    today = date.today()

    with transaction.atomic():
        # Update daily activity
        daily, created = UserDailyActivity.objects.get_or_create(
            user_id=user_id,
            activity_date=today,
            defaults={
                "id": str(uuid.uuid4()),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            },
        )

        if event.event_type == "task.completed":
            daily.has_task = True
            daily.task_count += 1
            daily.karma_earned += metadata.get("karma", 0)

            # Update IG karma if applicable
            ig_id = metadata.get("ig_id")
            if ig_id:
                ig_karma, _ = UserIgKarma.objects.get_or_create(
                    user_id=user_id,
                    ig_id=ig_id,
                    defaults={
                        "id": str(uuid.uuid4()),
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    },
                )
                ig_karma.total_karma += metadata.get("karma", 0)
                ig_karma.task_count += 1
                ig_karma.last_activity = datetime.now()
                ig_karma.save()

            # Update skill progress
            for skill_id in metadata.get("skill_ids", []):
                progress, _ = UserSkillProgress.objects.get_or_create(
                    user_id=user_id,
                    skill_id=skill_id,
                    defaults={
                        "id": str(uuid.uuid4()),
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    },
                )
                progress.completed_task_count += 1
                progress.total_karma += metadata.get("karma", 0)
                progress.last_task_at = datetime.now()
                progress.save()

        elif event.event_type == "karma.awarded":
            daily.has_karma = True
            daily.karma_earned += metadata.get("karma", 0)

            ig_id = metadata.get("ig_id")
            if ig_id:
                ig_karma, _ = UserIgKarma.objects.get_or_create(
                    user_id=user_id,
                    ig_id=ig_id,
                    defaults={
                        "id": str(uuid.uuid4()),
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                    },
                )
                ig_karma.total_karma += metadata.get("karma", 0)
                ig_karma.last_activity = datetime.now()
                ig_karma.save()

        elif event.event_type == "user.login":
            daily.has_login = True

        daily.updated_at = datetime.now()
        daily.save()


# ============================================================================
# Achievement Claiming
# ============================================================================


def claim_achievement(user_id: str, achievement_id: str) -> dict:
    """
    Called when user claims an achievement.

    1. Verify eligibility via rule engine
    2. Issue achievement (idempotent)
    3. Queue VC generation if applicable

    Returns: {success: bool, message: str, vc_pending: bool}
    """
    from api.dashboard.achievement.rule_engine import RuleEvaluator
    from db.achievement import Achievement, AchievementRule, UserAchievementsLog

    # Check if already claimed
    existing = UserAchievementsLog.objects.filter(
        user_id=user_id, achievement_id=achievement_id
    ).first()

    if existing:
        return {"success": False, "message": "Achievement already claimed"}

    # Get active rule for this achievement
    rule = (
        AchievementRule.objects.filter(achievement_id=achievement_id, is_active=True)
        .order_by("-version")
        .first()
    )

    if not rule:
        return {"success": False, "message": "No active rule for this achievement"}

    # Evaluate eligibility
    evaluator = RuleEvaluator(user_id)
    result = evaluator.evaluate_rule(rule)

    if not result.eligible:
        return {
            "success": False,
            "message": f"Not eligible: {result.reason}",
            "progress": result.progress,
        }

    # Issue the achievement
    success = _issue_achievement(
        user_id=user_id,
        achievement_id=achievement_id,
        rule_version=result.rule_version,
        source="user_claim",
    )

    if success:
        achievement = Achievement.objects.get(id=achievement_id)
        return {
            "success": True,
            "message": "Achievement claimed successfully!",
            "vc_pending": achievement.has_vc,
            "achievement_name": achievement.name,
        }
    else:
        return {"success": False, "message": "Failed to claim achievement"}


def _issue_achievement(
    user_id: str,
    achievement_id: str,
    rule_version: int,
    source: str = "user_claim",
    performed_by: str = None,
) -> bool:
    """
    Issue achievement with idempotency guarantee.
    Called from claim_achievement (user action) or manual_issue (admin).
    Returns True if newly issued, False if already exists.
    """
    from db.achievement import UserAchievementsLog, Achievement, AchievementAuditLog

    try:
        with transaction.atomic():
            # Check if already issued (using unique constraint)
            existing = UserAchievementsLog.objects.filter(
                user_id=user_id, achievement_id=achievement_id
            ).first()

            if existing:
                return False  # Already issued - idempotent no-op

            # Create achievement record
            achievement_log = UserAchievementsLog.objects.create(
                id=str(uuid.uuid4()),
                user_id_id=user_id,
                achievement_id_id=achievement_id,
                rule_version=rule_version,
                is_issued=True,
                vc_url="",
                created_by_id=performed_by or user_id,
                updated_by_id=performed_by or user_id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )

            # Log audit
            AchievementAuditLog.objects.create(
                id=str(uuid.uuid4()),
                user_id=user_id,
                achievement_id=achievement_id,
                action="issued",
                rule_version=rule_version,
                metadata={"source": source},
                performed_by_id=performed_by,
                created_at=datetime.now(),
            )

            # Queue VC issuance if applicable
            achievement = Achievement.objects.get(id=achievement_id)
            if achievement.has_vc and achievement.template_id:
                issue_vc_async.delay(user_id, achievement_id, str(achievement_log.id))

            logger.info(f"Achievement issued: {achievement_id} to user {user_id}")
            return True

    except IntegrityError:
        # Unique constraint violation - already issued
        return False


@shared_task(bind=True, max_retries=5, default_retry_delay=300)
def issue_vc_async(self, user_id: str, achievement_id: str, log_id: str):
    """
    Issue Verifiable Credential via qseverse.
    Retries on failure, but achievement is already issued.
    """
    from db.achievement import UserAchievementsLog, Achievement, AchievementAuditLog
    from db.user import User

    try:
        user = User.objects.get(id=user_id)
        achievement = Achievement.objects.get(id=achievement_id)

        payload = {
            "api_key": settings.QSEVERSE_API_KEY,
            "subject_info": {
                "name": user.full_name,
                "email": user.email,
                "phone": user.mobile or "",
            },
            "credential_info": {
                "name": achievement.name,
                "description": achievement.description,
            },
            "template_id": achievement.template_id,
            "send_email": True,
        }

        response = requests.post(
            f"{settings.QSEVERSE_BASE_URL}api/issue_vc_app",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"ApiKey {settings.QSEVERSE_API_KEY}",
            },
            timeout=30,
        )
        response.raise_for_status()

        vc_data = response.json()
        vc_url = vc_data.get("vc_url", "")

        # Update achievement log with VC URL
        UserAchievementsLog.objects.filter(id=log_id).update(vc_url=vc_url)

        # Audit log
        AchievementAuditLog.objects.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            achievement_id=achievement_id,
            action="vc_issued",
            metadata={"vc_url": vc_url},
            created_at=datetime.now(),
        )

        logger.info(f"VC issued for achievement {achievement_id} user {user_id}")
        return {"status": "success", "vc_url": vc_url}

    except requests.RequestException as e:
        logger.error(f"VC issuance failed for {user_id}/{achievement_id}: {e}")

        # Log failure
        AchievementAuditLog.objects.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            achievement_id=achievement_id,
            action="vc_failed",
            metadata={"error": str(e), "retry": self.request.retries},
            created_at=datetime.now(),
        )

        raise self.retry(exc=e)


# ============================================================================
# Admin Operations
# ============================================================================


def manual_issue_achievement(
    user_id: str,
    achievement_id: str,
    performed_by: str,
) -> dict:
    """
    Manually issue an achievement (admin operation).
    Bypasses rule evaluation.
    """
    from db.achievement import Achievement

    success = _issue_achievement(
        user_id=user_id,
        achievement_id=achievement_id,
        rule_version=0,  # Manual issue has no rule version
        source="admin_manual",
        performed_by=performed_by,
    )

    if success:
        achievement = Achievement.objects.get(id=achievement_id)
        return {
            "success": True,
            "message": f"Achievement '{achievement.name}' issued to user",
            "vc_pending": achievement.has_vc,
        }
    else:
        return {"success": False, "message": "Achievement already issued or failed"}


def revoke_achievement(
    user_id: str,
    achievement_id: str,
    performed_by: str,
    reason: str = None,
) -> dict:
    """
    Revoke an achievement (admin operation).
    """
    from db.achievement import UserAchievementsLog, AchievementAuditLog

    achievement_log = UserAchievementsLog.objects.filter(
        user_id=user_id, achievement_id=achievement_id
    ).first()

    if not achievement_log:
        return {"success": False, "message": "Achievement not found for user"}

    # Delete the achievement log
    achievement_log.delete()

    # Audit log
    AchievementAuditLog.objects.create(
        id=str(uuid.uuid4()),
        user_id=user_id,
        achievement_id=achievement_id,
        action="revoked",
        metadata={"reason": reason},
        performed_by_id=performed_by,
        created_at=datetime.now(),
    )

    logger.info(f"Achievement {achievement_id} revoked from user {user_id}")
    return {"success": True, "message": "Achievement revoked successfully"}
