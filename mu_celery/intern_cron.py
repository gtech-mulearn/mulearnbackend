from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from db.intern import UserInternGuildLink, InternDailyTimesheet, InternTask
from utils.types import InternGuildStatus, InternTaskStatus

@shared_task
def intern_daily_status_cron():
    """
    Cron job to evaluate intern status.
    Rules:
    - >= 2 missed timesheets -> AT_RISK
    - >= 5 missed timesheets -> INACTIVE
    """
    active_interns = UserInternGuildLink.objects.filter(
        status__in=[InternGuildStatus.ACTIVE.value, InternGuildStatus.AT_RISK.value]
    )
    
    today = now().date()
    
    for intern in active_interns:
        missed_count = 0
        days_checked = 0
        days_back = 1
        
        while days_checked < 5:
            check_date = today - timedelta(days=days_back)
            days_back += 1
            
            if check_date.weekday() > 4:
                continue
                
            has_timesheet = InternDailyTimesheet.objects.filter(
                user_id=intern.user_id, entry_date=check_date
            ).exists()
            
            if not has_timesheet:
                missed_count += 1
                
            days_checked += 1
                
        new_status = intern.status
        if missed_count >= 5:
            new_status = InternGuildStatus.INACTIVE.value
        elif missed_count >= 2:
            new_status = InternGuildStatus.AT_RISK.value
        else:
            new_status = InternGuildStatus.ACTIVE.value
            
        if intern.status != new_status:
            intern.status = new_status
            intern.save()

@shared_task
def intern_task_deadline_cron():
    """
    Cron job to evaluate intern tasks deadline.
    Rules:
    - If deadline < today and status != COMPLETED and not verified -> OVERDUE
    """
    today = now().date()
    overdue_tasks = InternTask.objects.filter(
        deadline__lt=today,
        is_verified=False
    ).exclude(status=InternTaskStatus.COMPLETED.value).exclude(status=InternTaskStatus.OVERDUE.value)
    
    for task in overdue_tasks:
        task.status = InternTaskStatus.OVERDUE.value
        task.save()

