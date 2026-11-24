import calendar

from celery import shared_task
from datetime import timedelta
from db.intern import UserInternGuildLink, InternDailyTimesheet, InternTask, InternLeaveRequest
from utils.types import InternGuildStatus, InternTaskStatus, InternLeaveStatus
from utils.utils import DateTimeUtils

# Interns may still submit yesterday's timesheet today (IST), so the missed-day
# scan starts from the day before yesterday — a day that can still be
# submitted is never counted as missed.
MISSED_DAY_SCAN_START_OFFSET = 2

@shared_task
def intern_daily_status_cron():
    """
    Cron job to evaluate intern status.
    Rules:
    - >= 6 missed timesheets (out of last 10 working days) -> AT_RISK
    - >= 10 missed timesheets (out of last 10 working days) -> INACTIVE
    Working days are counted back from the day before yesterday (IST).
    """
    active_interns = UserInternGuildLink.objects.filter(
        status__in=[InternGuildStatus.ACTIVE.value, InternGuildStatus.AT_RISK.value]
    )
    
    # Same IST day boundaries as timesheet submission.
    today = DateTimeUtils.get_ist_today()
    
    # 1. Batch fetch all timesheets for the last 20 days (to cover 10 working days)
    date_range_start = today - timedelta(days=20)
    active_intern_user_ids = list(active_interns.values_list('user_id', flat=True))
    
    # Using set of tuples for O(1) lookup
    all_timesheets = set(
        InternDailyTimesheet.objects.filter(
            user_id__in=active_intern_user_ids,
            entry_date__gte=date_range_start,
            entry_date__lte=today
        ).values_list('user_id', 'entry_date')
    )
    
    # 2. Batch fetch all approved leaves for the last 10 days
    approved_leaves_qs = InternLeaveRequest.objects.filter(
        user_id__in=active_intern_user_ids,
        status=InternLeaveStatus.APPROVED.value,
        end_date__gte=date_range_start,
        start_date__lte=today
    ).values('user_id', 'start_date', 'end_date')
    
    # Map user_id to list of approved leaves
    approved_leaves_by_user = {}
    for leave in approved_leaves_qs:
        user_id = leave['user_id']
        if user_id not in approved_leaves_by_user:
            approved_leaves_by_user[user_id] = []
        approved_leaves_by_user[user_id].append((leave['start_date'], leave['end_date']))
        
    def is_on_leave(user_id, check_date):
        leaves = approved_leaves_by_user.get(user_id, [])
        for start, end in leaves:
            if start <= check_date <= end:
                return True
        return False

    for intern in active_interns:
        missed_count = 0
        days_checked = 0
        days_back = MISSED_DAY_SCAN_START_OFFSET
        
        while days_checked < 10:
            check_date = today - timedelta(days=days_back)
            days_back += 1
            
            # Skip weekends
            if check_date.weekday() > 4:
                continue
                
            # Skip approved leave days
            if is_on_leave(intern.user_id, check_date):
                days_checked += 1
                continue
                
            has_timesheet = (intern.user_id, check_date) in all_timesheets
            
            if not has_timesheet:
                missed_count += 1
                
            days_checked += 1
                
        new_status = intern.status
        if missed_count >= 10:
            new_status = InternGuildStatus.INACTIVE.value
        elif missed_count >= 6:
            new_status = InternGuildStatus.AT_RISK.value
        else:
            new_status = InternGuildStatus.ACTIVE.value
            
        if intern.status != new_status:
            intern.status = new_status
            # Limitation: No system-user convention exists for updated_by_id in cron jobs.
            # Leaving updated_by_id unchanged.
            intern.save(update_fields=['status'])
            
    # 2.5. Handle approved leaves starting today: transition to ON_LEAVE
    newly_on_leave = InternLeaveRequest.objects.filter(
        status=InternLeaveStatus.APPROVED.value,
        start_date__lte=today,
        end_date__gte=today
    ).values_list('user_id', flat=True)

    for user_id in newly_on_leave:
        guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()
        if guild_link and guild_link.status != InternGuildStatus.ON_LEAVE.value:
            guild_link.previous_status = guild_link.status
            guild_link.status = InternGuildStatus.ON_LEAVE.value
            guild_link.save(update_fields=['status', 'previous_status'])
            
    # 3. Handle ON_LEAVE -> ACTIVE restoration
    on_leave_interns = UserInternGuildLink.objects.filter(
        status=InternGuildStatus.ON_LEAVE.value
    )
    
    if on_leave_interns.exists():
        on_leave_intern_user_ids = list(on_leave_interns.values_list('user_id', flat=True))
        # Check active leaves covering today
        active_leaves_today = set(
            InternLeaveRequest.objects.filter(
                user_id__in=on_leave_intern_user_ids,
                status=InternLeaveStatus.APPROVED.value,
                start_date__lte=today,
                end_date__gte=today
            ).values_list('user_id', flat=True)
        )
        
        for intern in on_leave_interns:
            if intern.user_id not in active_leaves_today:
                restored_status = intern.previous_status or InternGuildStatus.ACTIVE.value
                valid_targets = [InternGuildStatus.ACTIVE.value, InternGuildStatus.AT_RISK.value]
                if restored_status not in valid_targets:
                    restored_status = InternGuildStatus.ACTIVE.value
                
                intern.status = restored_status
                intern.previous_status = None
                intern.save(update_fields=['status', 'previous_status'])

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

    - Window's first day: "review is open" to every intern who isn't INACTIVE
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

    recipients = UserInternGuildLink.objects.exclude(status=InternGuildStatus.INACTIVE.value)
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
