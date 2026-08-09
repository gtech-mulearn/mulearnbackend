"""μCoin domain-event producers.

Writes rows to event_outbox (db/mu_events.py) when coin-relevant things
happen; the Celery dispatcher (mu_celery/mucoin_events.py) delivers them to
mucoin-service. Contract: INTEGRATION.md in gtech-mulearn/mucoin-service.

Design constraints honored here:
- Strictly one-way: this module only ever INSERTs into event_outbox. It never
  writes karma, levels, wallets, or any other core table.
- Never break core flows: emit failures are logged, not raised — a broken
  outbox must not fail a karma appraisal or a level-up.
- user.level_up fires only on level INCREASES. UserLvlLink is a OneToOne
  updated in place and the grit system can move a learner down; the old level
  is captured in pre_save and compared in post_save.
"""
import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from db.mu_events import EventOutbox
from db.task import KarmaActivityLog, UserLvlLink
from db.user import UserReferralLink

logger = logging.getLogger(__name__)


def emit(event_type, muid, payload):
    try:
        EventOutbox.objects.create(event_type=event_type, muid=muid, payload=payload)
    except Exception:
        logger.exception("mu_events: failed to enqueue %s for %s", event_type, muid)


@receiver(pre_save, sender=UserLvlLink)
def capture_old_level(sender, instance, **kwargs):
    old = (
        UserLvlLink.objects.filter(pk=instance.pk).select_related("level").first()
        if instance.pk
        else None
    )
    instance._old_level_order = old.level.level_order if old else 0


@receiver(post_save, sender=UserLvlLink)
def on_level_change(sender, instance, created, **kwargs):
    old = getattr(instance, "_old_level_order", 0)
    new = instance.level.level_order
    if new > old:
        emit(
            "user.level_up",
            instance.user.muid,
            {"muid": instance.user.muid, "old_level": old, "new_level": new},
        )


@receiver(pre_save, sender=KarmaActivityLog)
def capture_old_appraisal(sender, instance, **kwargs):
    old = (
        KarmaActivityLog.objects.filter(pk=instance.pk)
        .values_list("appraiser_approved", flat=True)
        .first()
        if instance.pk
        else None
    )
    instance._was_appraiser_approved = bool(old)


@receiver(post_save, sender=KarmaActivityLog)
def on_task_appraised(sender, instance, created, **kwargs):
    # Fire once, on the transition into appraiser-approved. Later saves of the
    # same row (mentor-review fields etc.) don't re-emit. mucoin-service also
    # dedupes by event id and caps payouts per user, so duplicates would be
    # economically harmless anyway.
    if not instance.user or not instance.appraiser_approved:
        return
    if getattr(instance, "_was_appraiser_approved", False):
        return
    emit(
        "task.verified",
        instance.user.muid,
        {
            "muid": instance.user.muid,
            "task_hashtag": instance.task.hashtag,
            "task_id": instance.task.id,
        },
    )


@receiver(post_save, sender=UserReferralLink)
def on_referral_registered(sender, instance, created, **kwargs):
    # user_referral_link stores the pair (user=invitee, referral=inviter) and
    # an is_coin flag, but NOT the invite code — so the code cannot be included
    # here. Phase-3 stake settlement in mucoin-service will either match by the
    # inviter/invitee pair or the registration flow will be extended to thread
    # the code through. Until then this event carries what core knows.
    if not created:
        return
    emit(
        "user.registered_via_invite",
        instance.user.muid,
        {
            "invitee_muid": instance.user.muid,
            "inviter_muid": instance.referral.muid,
            "is_coin": instance.is_coin,
            "invite_code": None,
        },
    )
