from celery import shared_task
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce

from db.organization import Organization, UserOrganizationLink

BATCH_SIZE = 500


@shared_task
def refresh_org_aggregates():
    """Recompute `organization.cached_total_karma` / `.cached_member_count`.

    These are denormalised so the organisation list/search endpoint can sort and
    paginate on them with an index instead of aggregating every member of every
    organisation on each request.

    One grouped pass over user_organization_link, not a correlated subquery per
    organisation. Organisations with no verified members are reset to zero so
    stale values cannot survive a member leaving.

    Safe to run repeatedly; returns the number of rows written.
    """
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
