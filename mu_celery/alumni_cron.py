from celery import shared_task
from django.utils.timezone import now

from db.organization import UserOrganizationLink


@shared_task
def update_alumni_status_cron():
    """
    Cron job to automatically mark users as alumni based on their graduation year.

    Rules:
    - If graduation_year < current_year -> set is_alumni = True
    - No roles are modified, only the is_alumni flag is toggled.
    """
    current_year = now().year

    updated_count = UserOrganizationLink.objects.filter(
        is_alumni=False,
        graduation_year__isnull=False,
        graduation_year__lt=str(current_year),
    ).update(is_alumni=True)

    return f"Alumni status updated for {updated_count} user(s)."
