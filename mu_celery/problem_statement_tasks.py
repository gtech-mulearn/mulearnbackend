from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from db.problem_statement import ProblemStatement, ProblemStatementAuditLog
from api.dashboard.problem_statement.ps_logger import log_ps_action


@shared_task
def close_expired_problem_statements():
    """
    Nightly task to close published problem statements whose deadline has passed.
    Uses select_for_update() to prevent race conditions and avoid overwriting later transitions.
    """
    now = timezone.now()
    expired_ids = list(
        ProblemStatement.objects.filter(
            status=ProblemStatement.Status.PUBLISHED,
            deadline__isnull=False,
            deadline__lt=now,
            deleted_at__isnull=True,
        ).values_list('id', flat=True)
    )

    closed_count = 0
    for ps_id in expired_ids:
        loop_now = timezone.now()
        with transaction.atomic():
            ps_locked = ProblemStatement.objects.select_for_update().filter(
                id=ps_id,
                status=ProblemStatement.Status.PUBLISHED,
                deadline__isnull=False,
                deadline__lt=loop_now,
                deleted_at__isnull=True,
            ).first()

            if not ps_locked:
                continue

            ps_locked.status = ProblemStatement.Status.CLOSED
            ps_locked.closed_at = loop_now
            ps_locked.updated_by_id = settings.SYSTEM_ADMIN_ID
            ps_locked.save(update_fields=['status', 'closed_at', 'updated_by', 'updated_at'])

            log_ps_action(
                problem_statement=ps_locked,
                action=ProblemStatementAuditLog.Action.CLOSED,
                actor_id=settings.SYSTEM_ADMIN_ID,
                actor_role="System/Cron",
                metadata={"reason": "Auto-closed by nightly cron due to passed deadline"},
            )
            closed_count += 1

    return f"Closed {closed_count} expired problem statements."
