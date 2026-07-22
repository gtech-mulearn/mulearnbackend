from celery import shared_task
from django.db.models import Q
from django.utils.timezone import now

from db.organization import UserOrganizationLink
from utils.types import OrganizationType


@shared_task
def update_alumni_status_cron():
    """Synchronize college alumni status with graduation year.

    A user is an alumnus only when their four-digit graduation year is before
    the current year. This corrects both stale alumni and stale non-alumni
    values, so it is safe to run repeatedly.
    """
    current_year = str(now().year)
    valid_college_links = UserOrganizationLink.objects.filter(
        org__org_type=OrganizationType.COLLEGE.value,
        graduation_year__regex=r"^[0-9]{4}$",
    )

    marked_alumni = valid_college_links.filter(
        graduation_year__lt=current_year,
    ).filter(
        Q(is_alumni=False) | Q(is_alumni__isnull=True)
    ).update(is_alumni=True)

    marked_student = valid_college_links.filter(
        graduation_year__gte=current_year,
        is_alumni=True,
    ).update(is_alumni=False)

    return {
        "marked_alumni": marked_alumni,
        "marked_student": marked_student,
    }
