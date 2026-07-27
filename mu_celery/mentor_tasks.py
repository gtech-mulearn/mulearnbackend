from celery import shared_task
from django.utils.timezone import now

from db.user import MentorApplication, MentorScopeGrant


@shared_task
def expire_stale_applications():
    """
    Addon §6.2 — nomination/application expiry. PENDING MentorApplication
    rows past their nomination_expires_at are auto-rejected so they don't
    quietly linger, and the applicant is notified.
    """
    from api.notification.notifications_utils import NotificationUtils
    from db.user import User
    from django.conf import settings

    system_actor = User.every.filter(id=settings.SYSTEM_ADMIN_ID).first()
    stale = MentorApplication.objects.filter(
        status=MentorApplication.Status.PENDING,
        nomination_expires_at__lt=now(),
    ).select_related('user')

    for application in stale:
        application.status = MentorApplication.Status.REJECTED
        application.verification_note = "Auto-rejected: nomination expired without action."
        application.updated_by_id = settings.SYSTEM_ADMIN_ID
        application.save(update_fields=["status", "verification_note", "updated_by_id"])

        try:
            NotificationUtils.insert_notification(
                user=application.user,
                title="Mentor Application Expired",
                description=(
                    f"Your {application.tier} mentor application expired without a decision "
                    f"and has been automatically closed. You may re-apply."
                ),
                button=None,
                url=None,
                created_by=system_actor,
            )
        except Exception:
            pass

    return len(stale)


@shared_task
def expire_stale_grants():
    """
    Addon §6.8 — grant expiry / periodic re-verification. Active
    MentorScopeGrant rows past their expires_at are soft-revoked (system
    actor), reusing the existing "Scope grant revoked" notification.
    """
    from api.notification.notifications_utils import NotificationUtils
    from db.user import User
    from django.conf import settings

    system_actor = User.every.filter(id=settings.SYSTEM_ADMIN_ID).first()
    stale = MentorScopeGrant.objects.filter(
        is_active=True,
        expires_at__isnull=False,
        expires_at__lt=now(),
    ).select_related('mentor__user')

    count = 0
    for grant in stale:
        grant.is_active = False
        grant.revoked_by_id = settings.SYSTEM_ADMIN_ID
        grant.revoked_at = now()
        grant.save(update_fields=["is_active", "revoked_by_id", "revoked_at"])
        count += 1

        try:
            NotificationUtils.insert_notification(
                user=grant.mentor.user,
                title="Mentor Scope Grant Expired",
                description=(
                    f"Your {grant.scope_type} mentor authority has expired and been "
                    f"revoked. Contact an admin if this needs renewal."
                ),
                button=None,
                url=None,
                created_by=system_actor,
            )
        except Exception:
            pass

    return count
