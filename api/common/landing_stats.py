"""The landing-page counters: members, organizations, interest groups and karma.

Moved out of api/common/common_consumer.py (issue 0030), so that module and api/common/signals.py
can both use it without signals.py importing Channels.
"""

from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from db.learning_circle import LearningCircle
from db.organization import Organization
from db.task import InterestGroup, KarmaActivityLog
from db.user import User, UserRoleLink
from utils.types import OrganizationType


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
