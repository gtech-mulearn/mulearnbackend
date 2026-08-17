from celery import shared_task
from django.core.cache import cache
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from db.organization import Organization, UserOrganizationLink

BATCH_SIZE = 500

# Guards against overlapping runs: this task is scheduled every 15 minutes
# (settings.CELERY_BEAT_SCHEDULE), but a full-table scan can outlast that on a
# large organization table, especially under the DB load this task exists to
# reduce. `cache.add` is an atomic SETNX against Redis, so only one worker can
# hold the lock at a time. The timeout is a safety net below the schedule
# interval so a worker that crashes mid-run can't wedge the lock forever.
LOCK_KEY = "org_aggregates_cron_lock"
LOCK_TIMEOUT = 60 * 14


@shared_task
def refresh_org_aggregates():
    """Recompute `organization.cached_total_karma` / `.cached_member_count`.

    These are denormalised so the organisation list/search endpoint can sort and
    paginate on them with an index instead of aggregating every member of every
    organisation on each request.

    One grouped pass over user_organization_link, not a correlated subquery per
    organisation. Organisations with no verified members are reset to zero so
    stale values cannot survive a member leaving.

    Safe to run repeatedly; returns the number of rows written, or -1 if a run
    was already in progress and this call skipped.
    """
    if not cache.add(LOCK_KEY, "1", LOCK_TIMEOUT):
        return -1

    try:
        return _refresh_org_aggregates()
    finally:
        cache.delete(LOCK_KEY)


def _refresh_org_aggregates():
    totals = (
        UserOrganizationLink.objects.filter(verified=True)
        .values("org_id")
        .annotate(
            karma=Coalesce(Sum("user__wallet_user__karma"), 0),
            members=Count("id"),
        )
    )
    aggregates = {
        row["org_id"]: (row["karma"], row["members"]) for row in totals.iterator()
    }

    to_update = []
    org_rows = Organization.objects.only(
        "id", "cached_total_karma", "cached_member_count"
    ).iterator()
    for org in org_rows:
        karma, members = aggregates.get(org.id, (0, 0))
        if org.cached_total_karma != karma or org.cached_member_count != members:
            org.cached_total_karma = karma
            org.cached_member_count = members
            to_update.append(org)

    if to_update:
        Organization.objects.bulk_update(
            to_update,
            ["cached_total_karma", "cached_member_count"],
            batch_size=BATCH_SIZE,
        )

    return len(to_update)
