"""
React to email changes (spec A §3.7). Registered from ApiConfig.ready().

Password-reset links and login OTPs were mailed to the OLD inbox, so they are
revoked; that is also what makes the §3.6 proofs safe. A verified old inbox
is told about the change.
"""
import logging
from zoneinfo import ZoneInfo

from django.db import transaction
from django.dispatch import receiver
from django.utils import timezone

from db.signals import user_email_changed
from db.user import ForgotPassword, OtpVerification
from utils.emails import mask_email
from utils.utils import send_template_mail

from . import codes

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


@receiver(user_email_changed, dispatch_uid="email_verification.on_user_email_changed")
def on_user_email_changed(sender, user, old_email, old_was_verified, **kwargs):
    handle_email_changed(user=user, old_email=old_email, old_was_verified=old_was_verified)


def handle_email_changed(user, old_email, old_was_verified):
    ForgotPassword.objects.filter(user_id=user.id).delete()
    OtpVerification.objects.filter(user_id=user.id).delete()
    codes.revoke_codes(user.id)
    if old_was_verified:
        new_email = user.email
        transaction.on_commit(lambda: _notify_old_address(old_email, new_email))


def _notify_old_address(old_email, new_email):
    try:
        send_template_mail(
            context={
                "email": old_email,
                "new_email_masked": mask_email(new_email),
                "changed_at": timezone.now().astimezone(IST).strftime("%d %b %Y, %I:%M %p IST"),
            },
            subject="Your µLearn email was changed",
            address=["email_verification", "email_changed.html"],
        )
    except Exception:
        logger.exception("email_verification email_changed_notice_failed to=%s", mask_email(old_email))
