import collections

from celery import shared_task
from django.core.cache import cache
from django.db.models import Sum

from db.learning_circle import LearningCircle, UserCircleLink
from db.task import KarmaActivityLog

BATCH_SIZE = 500

# Same reasoning as mu_celery/org_aggregates_cron.py's LOCK_KEY/LOCK_TIMEOUT:
# cache.add is an atomic SETNX, so only one worker holds the lock at a time;
# the timeout sits below the schedule interval so a crashed worker can't wedge it.
LOCK_KEY = "learning_circle_aggregates_cron_lock"
LOCK_TIMEOUT = 60 * 14


@shared_task
def refresh_learning_circle_aggregates():
    """Recompute `learning_circle.cached_total_karma` / `.cached_rank`.

    A circle's rank is a comparison of its members' karma (scoped to the
    circle's own interest group) against every other circle's -- there's no
    way to answer "where does this circle rank" without knowing every other
    circle's total, so it can't be made cheap on the request path no matter
    how it's scoped. This mirrors org_aggregates_cron.py's approach: do the
    expensive aggregation once here on a schedule, and let
    LearningCircleDetailSerializer just read the precomputed columns.

    Safe to run repeatedly; returns the number of rows written, or -1 if a
    run was already in progress and this call skipped.
    """
    if not cache.add(LOCK_KEY, "1", LOCK_TIMEOUT):
        return -1

    try:
        return _refresh_learning_circle_aggregates()
    finally:
        cache.delete(LOCK_KEY)


def _refresh_learning_circle_aggregates():
    circle_to_users = collections.defaultdict(list)
    for link in UserCircleLink.objects.filter(accepted=True).values("circle_id", "user_id"):
        circle_to_users[link["circle_id"]].append(link["user_id"])

    circle_igs = dict(LearningCircle.objects.values_list("id", "ig_id"))

    user_ig_karma = collections.defaultdict(int)
    for entry in (
        KarmaActivityLog.objects.values("user_id", "task__ig").annotate(total_karma=Sum("karma"))
    ):
        user_ig_karma[(entry["user_id"], entry["task__ig"])] += entry["total_karma"] or 0

    totals = {}
    for circle_id, ig_id in circle_igs.items():
        member_ids = circle_to_users.get(circle_id, [])
        totals[circle_id] = sum(user_ig_karma.get((uid, ig_id), 0) for uid in member_ids)

    ranked_ids = sorted(totals, key=lambda circle_id: totals[circle_id], reverse=True)
    ranks = {circle_id: i + 1 for i, circle_id in enumerate(ranked_ids)}

    to_update = []
    circle_rows = LearningCircle.objects.only("id", "cached_total_karma", "cached_rank").iterator()
    for circle in circle_rows:
        karma = totals.get(circle.id, 0)
        rank = ranks.get(circle.id, 0)
        if circle.cached_total_karma != karma or circle.cached_rank != rank:
            circle.cached_total_karma = karma
            circle.cached_rank = rank
            to_update.append(circle)

    if to_update:
        LearningCircle.objects.bulk_update(
            to_update, ["cached_total_karma", "cached_rank"], batch_size=BATCH_SIZE
        )

    return len(to_update)
