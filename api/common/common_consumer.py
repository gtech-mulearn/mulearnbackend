import json

from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from db.learning_circle import LearningCircle
from db.learning_circle import UserCircleLink
from db.organization import Organization
from db.task import InterestGroup, KarmaActivityLog, TaskList, UserIgLink
from db.user import User, UserRoleLink
from db.organization import UserOrganizationLink
from db.mentor import MentorshipSession
from django.core.cache import cache

from utils.types import IntegrationType, OrganizationType

class LandingStats:
    data = {}

    def members_count(self):
        members_count = User.objects.all().count()
        return members_count

    def org_type_counts(self):
        org_type_counts = Organization.objects.filter(
                org_type__in=[OrganizationType.COLLEGE.value, OrganizationType.COMPANY.value,
                                OrganizationType.COMMUNITY.value]
            ).values('org_type').annotate(org_count=Coalesce(Count('org_type'), 0))
        org_type_counts = list(org_type_counts)

        return org_type_counts

    def enablers_mentors_count(self):
        enablers_mentors_count = UserRoleLink.objects.filter(
            role__title__in=["Mentor", "Enabler"]).values(
            'role__title').annotate(role_count=Coalesce(Count('role__title'), 0))
        enablers_mentors_count = list(enablers_mentors_count)

        return enablers_mentors_count

    def interest_groups_count(self):
        interest_groups_count = InterestGroup.objects.all().count()
        return interest_groups_count

    def learning_circles_count(self):
        learning_circles_count = LearningCircle.objects.all().count()
        return learning_circles_count
    
    def karma_pow_count(self):
        karma_pow_count = KarmaActivityLog.objects.aggregate(karma_count=Coalesce(Sum('karma'), 0), pow_count=Count('id'))
        return karma_pow_count

    # Each part of the landing-page payload is cached on its own under a fixed
    # key (six keys in total, so the key space cannot grow). Every one of these
    # is a full-table aggregate, and `karma_pow_count` scans all of
    # karma_activity_log, so they must not run once per websocket client.
    #
    # Invalidation: a create/delete of the model behind a part recomputes just
    # that part (see db_signals below). `karma_pow_count` has no signal on
    # purpose (karma is written far too often), so it is refreshed by TTL only
    # and can lag by up to CACHE_TTL.
    CACHE_TTL = 60 * 5
    CACHE_PREFIX = "landing_stats:"
    PARTS = {
        'members': 'members_count',
        'org_type_counts': 'org_type_counts',
        'enablers_mentors_count': 'enablers_mentors_count',
        'ig_count': 'interest_groups_count',
        'learning_circle_count': 'learning_circles_count',
        'karma_pow_count': 'karma_pow_count',
    }
    PART_FOR_SENDER = {
        User: 'members',
        Organization: 'org_type_counts',
        UserRoleLink: 'enablers_mentors_count',
        InterestGroup: 'ig_count',
        LearningCircle: 'learning_circle_count',
    }

    def _compute(self, part):
        return getattr(self, self.PARTS[part])()

    def refresh(self, part):
        """Recompute one part from the database and store it."""
        value = self._compute(part)
        try:
            cache.set(self.CACHE_PREFIX + part, value, self.CACHE_TTL)
        except Exception:
            # The cache is an optimisation; the numbers must still be served
            # (straight from the database) when Redis is unavailable.
            pass
        return value

    def snapshot(self, parts=None):
        """Return {part: value}, reading the cache and computing only the misses."""
        parts = list(parts or self.PARTS)
        try:
            cached = cache.get_many([self.CACHE_PREFIX + part for part in parts])
        except Exception:
            cached = {}
        data = {}
        for part in parts:
            key = self.CACHE_PREFIX + part
            data[part] = cached[key] if key in cached else self.refresh(part)
        return data

    def get_data(self, sender):
        if sender is None:
            self.data = self.snapshot()
        else:
            part = self.PART_FOR_SENDER.get(sender)
            if part:
                self.refresh(part)
            self.data = self.snapshot()


landing_stats = LandingStats()

class GlobalCount(WebsocketConsumer):
    data = {}
    group_name = "landing_stats"

    def connect(self):
        async_to_sync(self.channel_layer.group_add)(
                self.group_name, 
                self.channel_name
            )
        self.accept()

        self.data = landing_stats.snapshot()

        self.send(text_data=json.dumps(self.data))
    
    def disconnect(self, code):
        # group_discard is a coroutine: without async_to_sync it was never
        # awaited, so closed sockets stayed in the group until Redis expired them.
        async_to_sync(self.channel_layer.group_discard)(
            self.group_name,
            self.channel_name
        )
    
    def send_data(self, event):
        self.send(text_data=json.dumps(event['data']))

channel_layer = get_channel_layer()
    
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
        async_to_sync(channel_layer.group_send)(
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
