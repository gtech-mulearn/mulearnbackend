from celery import shared_task
from django.utils.timezone import now
from datetime import timedelta
from db.intern import UserInternGuildLink, InternDailyTimesheet
from utils.types import InternGuildStatus

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
        for i in range(1, 6):
            check_date = today - timedelta(days=i)
            
            # Simple check, we assume 5 consecutive previous days
            has_timesheet = InternDailyTimesheet.objects.filter(
                user_id=intern.user_id, entry_date=check_date
            ).exists()
            
            if not has_timesheet:
                missed_count += 1
                
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
