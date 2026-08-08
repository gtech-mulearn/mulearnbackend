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
        # No rule - fall back to an admin-granted eligibility (e.g. from bulk-issue)
        return _claim_via_eligibility_grant(user_id, achievement_id)

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


def _claim_via_eligibility_grant(user_id: str, achievement_id: str) -> dict:
    """
    Claim an achievement that has no active rule, using a pending
    admin-granted eligibility (created by bulk-issue for VC achievements).
    """
    from db.achievement import Achievement, AchievementEligibilityGrant

    grant = AchievementEligibilityGrant.objects.filter(
        user_id=user_id, achievement_id=achievement_id, status="pending"
    ).first()

    if not grant:
        return {"success": False, "message": "No active rule for this achievement"}

    success = _issue_achievement(
        user_id=user_id,
        achievement_id=achievement_id,
        rule_version=0,
        source="manual_grant_claim",
    )

    if not success:
        return {"success": False, "message": "Failed to claim achievement"}

    grant.status = "claimed"
    grant.save(update_fields=["status", "updated_at"])

    achievement = Achievement.objects.get(id=achievement_id)
    return {
        "success": True,
        "message": "Achievement claimed successfully!",
        "vc_pending": achievement.has_vc,
        "achievement_name": achievement.name,
    }


def grant_achievement_eligibility(
    user_id: str,
    achievement_id: str,
    granted_by: str,
) -> dict:
    """
    Grant a user eligibility to claim an achievement (admin operation, e.g.
    bulk-issue of VC achievements) without issuing it directly. The user
    claims it themselves later - picking their DID and issuing the VC.
    """
    from db.achievement import Achievement, AchievementEligibilityGrant, UserAchievementsLog

    if UserAchievementsLog.objects.filter(
        user_id=user_id, achievement_id=achievement_id
    ).exists():
        return {"success": False, "message": "Achievement already issued"}

    try:
        with transaction.atomic():
            existing = (
                AchievementEligibilityGrant.objects.select_for_update()
                .filter(user_id=user_id, achievement_id=achievement_id)
                .first()
            )

            if existing:
                if existing.status == "pending":
                    return {"success": False, "message": "Already eligible"}

                # revoked (or claimed but the issued log was separately
                # deleted) - re-grant by resetting the existing row instead
                # of inserting a new one (unique_together blocks that).
                existing.status = "pending"
                existing.granted_by_id = granted_by
                existing.source = "bulk_issue"
                existing.updated_at = datetime.now()
                existing.save(
                    update_fields=["status", "granted_by", "source", "updated_at"]
                )
            else:
                AchievementEligibilityGrant.objects.create(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    achievement_id=achievement_id,
                    status="pending",
                    granted_by_id=granted_by,
                    source="bulk_issue",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
    except IntegrityError:
        return {"success": False, "message": "Already eligible"}

    achievement = Achievement.objects.get(id=achievement_id)
    return {
        "success": True,
        "message": f"Eligibility granted for '{achievement.name}'",
    }


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

            # NOTE: VC issuance is NOT automatic. Users must claim VCs themselves
            # from their profile dashboard by clicking "Issue VC".
            # The frontend calls Qseverse directly and then updates vc_url via API.

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
    from db.achievement import UserAchievementsLog, AchievementAuditLog, AchievementEligibilityGrant

    achievement_log = UserAchievementsLog.objects.filter(
        user_id=user_id, achievement_id=achievement_id
    ).first()

    if not achievement_log:
        grant = AchievementEligibilityGrant.objects.filter(
            user_id=user_id, achievement_id=achievement_id, status="pending"
        ).first()

        if not grant:
            return {"success": False, "message": "Achievement not found for user"}

        grant.status = "revoked"
        grant.save(update_fields=["status", "updated_at"])
        return {"success": True, "message": "Eligibility grant revoked successfully"}

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


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def bulk_check_and_issue_achievements(
    self, date_from_str: str, date_to_str: str, performed_by_id: str = None
):
    """
    Check and issue all eligible achievements for users active within the given date range.
    """
    from db.task import KarmaActivityLog
    from api.dashboard.achievement.rule_engine import RuleEvaluator

    try:
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)

        # 1. Get unique users active in the range
        user_ids = list(
            KarmaActivityLog.objects.filter(
                updated_at__date__range=[date_from, date_to],
                appraiser_approved=True,
            )
            .values_list("user_id", flat=True)
            .distinct()
        )

        logger.info(
            f"Bulk sync: Processing {len(user_ids)} users active between {date_from} and {date_to}"
        )

        issued_count = 0

        for user_id in user_ids:
            try:
                evaluator = RuleEvaluator(str(user_id))
                eligible_results = evaluator.get_eligible_achievements()

                for result in eligible_results:
                    if result.eligible:
                        success = _issue_achievement(
                            user_id=str(user_id),
                            achievement_id=result.achievement_id,
                            rule_version=result.rule_version,
                            source="bulk_sync",
                            performed_by=performed_by_id,
                        )
                        if success:
                            issued_count += 1
            except Exception as e:
                logger.error(f"Error processing user {user_id} in bulk sync: {e}")

        logger.info(
            f"Bulk sync complete. Users: {len(user_ids)}, Issued: {issued_count}"
        )
        return {
            "status": "success",
            "users_processed": len(user_ids),
            "achievements_issued": issued_count,
        }

    except Exception as e:
        logger.exception(f"Bulk sync failed: {e}")
        raise self.retry(exc=e)
