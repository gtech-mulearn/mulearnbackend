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
    """
    expired_statements = ProblemStatement.objects.filter(
        status=ProblemStatement.Status.PUBLISHED,
        deadline__isnull=False,
        deadline__lt=timezone.now(),
        deleted_at__isnull=True,
    )

    closed_count = 0
    for ps in expired_statements:
        now = timezone.now()
        with transaction.atomic():
            ps.status = ProblemStatement.Status.CLOSED
            ps.closed_at = now
            ps.updated_by_id = settings.SYSTEM_ADMIN_ID
            ps.save(update_fields=['status', 'closed_at', 'updated_by', 'updated_at'])

            log_ps_action(
                problem_statement=ps,
                action=ProblemStatementAuditLog.Action.CLOSED,
                actor_id=settings.SYSTEM_ADMIN_ID,
                actor_role="System/Cron",
                metadata={"reason": "Auto-closed by nightly cron due to passed deadline"},
            )
            closed_count += 1

    return f"Closed {closed_count} expired problem statements."
