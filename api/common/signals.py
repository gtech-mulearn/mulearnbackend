"""Model signal receivers: landing-page stats and mentor-dashboard cache invalidation.

Registered by ApiConfig.ready() (api/apps.py), so they run in every process that writes these
models, Celery workers included. Until issue 0030 they lived in api/common/common_consumer.py
and were registered only when the WebSocket routing imported it.
"""

from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from api.common.landing_stats import landing_stats
from db.learning_circle import LearningCircle
from db.mentor import MentorshipSession
from db.organization import Organization, UserOrganizationLink
from db.task import InterestGroup, KarmaActivityLog, TaskList, UserIgLink
from db.user import User, UserRoleLink


@receiver(post_save, sender=User)
@receiver(post_save, sender=LearningCircle)
@receiver(post_save, sender=InterestGroup)
@receiver(post_save, sender=UserRoleLink)
@receiver(post_save, sender=Organization)
@receiver(post_delete, sender=User)
@receiver(post_delete, sender=LearningCircle)
@receiver(post_delete, sender=InterestGroup)
@receiver(post_delete, sender=UserRoleLink)
@receiver(post_delete, sender=Organization)
def db_signals(sender, instance, created=None, *args, **kwargs):
    if created or created == None:
        # Run after the surrounding transaction commits (immediately when there
        # is none): the count then includes the new row, and neither the COUNT
        # nor the Redis publish extends the writer's transaction and row locks.
        transaction.on_commit(lambda: _broadcast_landing_stats(sender))


def _broadcast_landing_stats(sender):
    try:
        landing_stats.get_data(sender)
        # Imported here, not at module level, so registering these receivers never imports
        # Channels. The broadcast goes when Channels is retired (issue 0034).
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        async_to_sync(get_channel_layer().group_send)(
            "landing_stats",
            {"type": "send_data", "data": landing_stats.data}
        )
    except Exception:
        # Landing-page counters are best effort; they must never fail the write
        # that triggered them.
        pass

def invalidate_scope_cache(scope_type, scope_id):
    if scope_id:
        try:
            cache.delete(f"mentor_dash_scope:{scope_type}:{scope_id}")
        except Exception:
            pass

@receiver(post_save, sender=UserOrganizationLink)
@receiver(post_delete, sender=UserOrganizationLink)
def handle_org_link_cache(sender, instance, **kwargs):
    if instance.org_id:
        invalidate_scope_cache("CAMPUS_MENTOR", instance.org_id)
        invalidate_scope_cache("COMPANY_MENTOR", instance.org_id)

@receiver(post_save, sender=UserIgLink)
@receiver(post_delete, sender=UserIgLink)
def handle_ig_link_cache(sender, instance, **kwargs):
    if instance.ig_id:
        invalidate_scope_cache("IG_MENTOR", instance.ig_id)

@receiver(post_save, sender=MentorshipSession)
@receiver(post_delete, sender=MentorshipSession)
def handle_session_cache(sender, instance, **kwargs):
    if instance.entity_id:
        if instance.session_type == MentorshipSession.SessionType.CAMPUS_SESSION:
            invalidate_scope_cache("CAMPUS_MENTOR", instance.entity_id)
        elif instance.session_type == MentorshipSession.SessionType.COMPANY_SESSION:
            invalidate_scope_cache("COMPANY_MENTOR", instance.entity_id)
        elif instance.session_type == MentorshipSession.SessionType.IG_SESSION:
            invalidate_scope_cache("IG_MENTOR", instance.entity_id)

@receiver(post_save, sender=KarmaActivityLog)
@receiver(post_delete, sender=KarmaActivityLog)
def handle_karma_cache(sender, instance, **kwargs):
    if not instance.task_id:
        return
    # Use the task if the caller already loaded it; otherwise fetch only the two
    # ids needed instead of lazy-loading the whole TaskList row on every write.
    task = instance._state.fields_cache.get("task")
    if task is not None:
        org_id, ig_id = task.org_id, task.ig_id
    else:
        org_id, ig_id = (
            TaskList.objects.filter(pk=instance.task_id)
            .values_list("org_id", "ig_id")
            .first()
            or (None, None)
        )
    if org_id:
        invalidate_scope_cache("COMPANY_MENTOR", org_id)
    if ig_id:
        invalidate_scope_cache("IG_MENTOR", ig_id)
