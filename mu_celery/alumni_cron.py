from celery import shared_task
from django.db.models import Q
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
        Q(is_alumni=False) | Q(is_alumni__isnull=True),  # explicit check for False and NULL
        graduation_year__isnull=False,
        graduation_year__regex=r'^[0-9]{4}$',  # exclude malformed values (e.g. "25", "2025-06") before comparison
        graduation_year__lt=str(current_year),
    ).update(is_alumni=True)

    return f"Alumni status updated for {updated_count} user(s)."
