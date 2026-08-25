from celery import shared_task
from django.utils.timezone import now

from db.job import CompanyJob


@shared_task
def expire_stale_jobs():
    """
    PRD §5.2 — auto-expiry scheduling: an Active job posting whose optional
    `expires_at` has passed is flipped to Expired (rather than being left to
    the company to manually close), with the poster notified.
    """
    from api.notification.notifications_utils import NotificationUtils
    from db.user import User
    from django.conf import settings

    system_actor = User.every.filter(id=settings.SYSTEM_ADMIN_ID).first()
    stale_jobs = CompanyJob.objects.filter(
        status=CompanyJob.Status.ACTIVE,
        expires_at__lt=now(),
        is_deleted=False,
    ).select_related("created_by")

    for job in stale_jobs:
        job.status = CompanyJob.Status.EXPIRED
        job.updated_at = now()
        job.save(update_fields=["status", "updated_at"])

        if job.created_by:
            try:
                NotificationUtils.insert_notification(
                    user=job.created_by,
                    title="Job Posting Expired",
                    description=f'Your job posting "{job.title}" has expired. Repost or extend it to keep it visible.',
                    button=None,
                    url=None,
                    created_by=system_actor,
                )
            except Exception:
                import logging
                logging.getLogger(__name__).exception("Failed to notify on job auto-expiry")
