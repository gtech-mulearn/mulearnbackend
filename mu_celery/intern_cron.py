import calendar

from celery import shared_task
from django.db import transaction
from db.intern import UserInternTeamLink, InternTask, InternLeaveRequest
from db.user import UserRoleLink
from utils.intern_permissions import (
    INACTIVE, LEAD_ROLE, ON_LEAVE, holds_role_subquery, in_tenure, members_only, system_history_row,
    working_members,
)
from utils.types import InternHistoryAction, InternStatus, InternTaskStatus, InternLeaveStatus, RoleType
from utils.utils import DateTimeUtils


@shared_task
def intern_daily_status_cron():
    """
    Leave only: puts interns ON_LEAVE when approved leave covers today (IST) and
    gives them their earlier status back when it no longer does. Nothing else
    changes status here (there is no AT_RISK or missed-timesheet rule any more).

    Works on current team rows inside their tenure; a row past its end_date is
    left to intern_tenure_end_cron (the tenure end wins over leave). Roles are
    never touched. Idempotent: re-running the same day changes nothing.
    """
    today = DateTimeUtils.get_ist_today()
    on_leave_today = set(
        InternLeaveRequest.objects.filter(
            status=InternLeaveStatus.APPROVED.value, start_date__lte=today, end_date__gte=today,
        ).values_list('user_id', flat=True)
    )

    # 1. Approved leave covering today -> ON_LEAVE (the status before is kept to restore later).
    for intern in in_tenure(members_only(UserInternTeamLink.objects.all()), today).filter(
        user_id__in=list(on_leave_today),
    ).exclude(intern_status__in=[ON_LEAVE, INACTIVE]):
        intern.previous_intern_status = intern.intern_status
        intern.intern_status = ON_LEAVE
        intern.status_reason = "On approved leave"
        intern.save(update_fields=['intern_status', 'previous_intern_status', 'status_reason', 'updated_at'])

    # 2. ON_LEAVE with no approved leave covering today -> the status before the leave.
    for intern in in_tenure(UserInternTeamLink.objects.filter(is_current=True, intern_status=ON_LEAVE), today):
        if intern.user_id in on_leave_today:
            continue
        restored = intern.previous_intern_status
        # INACTIVE is kept: someone marked INACTIVE before their leave stays INACTIVE.
        if restored not in (InternStatus.ACTIVE.value, InternStatus.INACTIVE.value):
            restored = InternStatus.ACTIVE.value
        intern.intern_status = restored
        intern.previous_intern_status = None
        intern.status_reason = "Approved leave ended"
        intern.save(update_fields=['intern_status', 'previous_intern_status', 'status_reason', 'updated_at'])


@shared_task
def intern_tenure_end_cron():
    """
    Ends tenures: a current row whose end_date has passed (IST) becomes INACTIVE
    (earlier status cleared, roles kept; the tenure end wins over leave). Each one
    gets a TENURE_ENDED history row (actor: system admin, role SYSTEM), and the
    team's working Lead(s) plus everyone holding Admins get INTERN_TENURE_ENDED.
    An Admin then extends the end date (back to ACTIVE) or deactivates them.

    Idempotent per row and end date: a row is picked once for each end_date (rows
    with a TENURE_ENDED history row for that date are skipped), and the notification
    is deduped on the same pair, so a row whose end date was extended is ended and
    notified again when the new date passes. Interns a Lead or Admin had already
    marked INACTIVE are included, so their tenure end is notified too.
    """
    from api.notification.audience import Audience
    from api.notification.service import NotificationService
    from api.notification.types import NotificationType

    from db.intern import InternHistory

    today = DateTimeUtils.get_ist_today()

    def handled(entity_ids):
        """{(row id, end_date)} already recorded as ended."""
        return {
            (entity_id, (old or {}).get('end_date'))
            for entity_id, old in InternHistory.objects.filter(
                entity_id__in=entity_ids, action=InternHistoryAction.TENURE_ENDED.value,
            ).values_list('entity_id', 'old_data')
        }

    candidates = list(
        members_only(UserInternTeamLink.objects.select_related('user', 'team')).filter(end_date__lt=today)
    )
    done = handled([str(link.id) for link in candidates])
    ended = [link for link in candidates if (str(link.id), link.end_date.isoformat()) not in done]
    if not ended:
        return

    admin_ids = set(
        UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value).values_list('user_id', flat=True)
    )
    leads_by_team = {}
    for team_id, user_id in (
        working_members(UserInternTeamLink.objects.filter(team_id__in={link.team_id for link in ended}))
        .filter(holds_role_subquery([LEAD_ROLE])).values_list('team_id', 'user_id')
    ):
        leads_by_team.setdefault(team_id, set()).add(user_id)

    for link in ended:
        with transaction.atomic():
            row = UserInternTeamLink.objects.select_for_update().filter(id=link.id, is_current=True).first()
            if row is None or row.end_date >= today or (str(row.id), row.end_date.isoformat()) in handled([str(row.id)]):
                continue
            old_status = row.intern_status
            row.intern_status = INACTIVE
            row.previous_intern_status = None
            row.status_reason = f"Tenure ended on {row.end_date:%d %b %Y}"
            row.save(update_fields=['intern_status', 'previous_intern_status', 'status_reason', 'updated_at'])
            system_history_row(
                InternHistoryAction.TENURE_ENDED.value, row,
                old={"status": old_status, "end_date": row.end_date.isoformat()},
                new={"status": INACTIVE},
                reason=row.status_reason,
            ).save()

            recipients = (leads_by_team.get(row.team_id, set()) | admin_ids) - {row.user_id}
            if recipients:
                NotificationService.dispatch(
                    notif_type=NotificationType.INTERN_TENURE_ENDED,
                    audience=Audience.users(list(recipients)),
                    context={
                        "full_name": link.user.full_name,
                        "muid": link.user.muid,
                        "team_name": link.team.name,
                        "end_date": row.end_date.strftime("%d %b %Y"),
                    },
                    entity_id=str(row.id),
                    occurrence=f"tenure_end:{row.end_date.isoformat()}",
                )


@shared_task
def intern_task_deadline_cron():
    """
    Cron job to evaluate intern tasks deadline.
    Rules:
    - If deadline < today (IST) and status != COMPLETED and not verified -> OVERDUE
    """
    today = DateTimeUtils.get_ist_today()
    overdue_tasks = InternTask.objects.filter(
        deadline__lt=today,
        is_verified=False
    ).exclude(status=InternTaskStatus.COMPLETED.value).exclude(status=InternTaskStatus.OVERDUE.value)
    
    for task in overdue_tasks:
        task.status = InternTaskStatus.OVERDUE.value
        task.save()


@shared_task
def intern_monthly_review_window_cron():
    """
    Monthly review window notifications. Scheduled daily at 00:05 IST.

    - Window's first day: "review is open" to every current team member who isn't INACTIVE
      (ON_LEAVE included — the notification waits in their list).
    - Window's last day: "last day" to the same interns, minus those who
      already have a PENDING or APPROVED review for the month.
    - Any other day: returns without querying.

    Idempotent: the dedupe key is "<type>:<YYYY-MM>:<open|last_day>", and the
    notification table is unique on (user_id, dedupe_key), so a re-run or a
    retry never notifies anyone twice.
    """
    from django.db import transaction

    from api.dashboard.intern.monthly_review.window import get_monthly_review_window
    from api.notification.audience import Audience
    from api.notification.service import NotificationService
    from api.notification.types import NotificationType
    from db.intern import InternMonthlyReview
    from utils.types import InternSubmissionStatus

    today = DateTimeUtils.get_ist_today()
    window = get_monthly_review_window(today)
    if not window.is_open:
        return

    if today == window.opens_on:
        notif_type, occurrence = NotificationType.INTERN_MONTHLY_REVIEW_OPEN, "open"
    elif today == window.closes_on:
        notif_type, occurrence = NotificationType.INTERN_MONTHLY_REVIEW_LAST_DAY, "last_day"
    else:
        return

    # Current team members inside their tenure who aren't INACTIVE.
    recipients = working_members(UserInternTeamLink.objects.all())
    if occurrence == "last_day":
        already_submitted = (
            InternMonthlyReview.objects
            .filter(year=window.year, month=window.month)
            .exclude(status=InternSubmissionStatus.REJECTED.value)
            .values('user_id')
        )
        recipients = recipients.exclude(user_id__in=already_submitted)

    user_ids = [str(uid) for uid in recipients.values_list('user_id', flat=True).distinct()]
    if not user_ids:
        return

    with transaction.atomic():
        NotificationService.dispatch(
            notif_type=notif_type,
            audience=Audience.users(user_ids),
            context={
                "month_name": calendar.month_name[window.month],
                "year": window.year,
                "closes_on": window.closes_on.strftime("%d %b"),
            },
            entity_id=f"{window.year}-{window.month:02d}",
            occurrence=occurrence,
        )
