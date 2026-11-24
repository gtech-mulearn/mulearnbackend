"""
Leave days for a monthly review, worked out on read — never stored.

Counts APPROVED intern_leave_request rows (every leave type, WFH included),
each clipped to the period, in calendar days — the same unit the leave module
uses for duration_days. A leave from Oct 30 to Nov 2 counts 2 days for
October and 2 for November.

Approved leaves for one intern never overlap (the leave serializer rejects
overlapping PENDING/APPROVED requests), so summing the clipped spans does not
double count. The lookups use idx_leave_user_status (user_id, status).
"""
from collections import defaultdict

from db.intern import InternLeaveRequest
from utils.types import InternLeaveStatus


def _overlap_days(start_date, end_date, period_start, period_end) -> int:
    return max(0, (min(end_date, period_end) - max(start_date, period_start)).days + 1)


def _approved_leaves(user_ids, period_start, period_end):
    return InternLeaveRequest.objects.filter(
        user_id__in=user_ids,
        status=InternLeaveStatus.APPROVED.value,
        start_date__lte=period_end,
        end_date__gte=period_start,
    ).values_list('user_id', 'start_date', 'end_date')


def approved_leave_days(user_id, period_start, period_end) -> int:
    """Approved leave days for one intern inside [period_start, period_end]."""
    if period_end < period_start:
        return 0
    return sum(
        _overlap_days(start, end, period_start, period_end)
        for _, start, end in _approved_leaves([user_id], period_start, period_end)
    )


def leave_days_by_review(reviews) -> dict:
    """
    {review_id: leave_days} for a page of reviews, each over its own month,
    in a single query. Pass the result to the serializer as
    context['leave_days'] so list endpoints don't run one query per row.
    """
    reviews = list(reviews)
    if not reviews:
        return {}

    by_user = defaultdict(list)
    for user_id, start, end in _approved_leaves(
        {review.user_id for review in reviews},
        min(review.period_start for review in reviews),
        max(review.period_end for review in reviews),
    ):
        by_user[user_id].append((start, end))

    return {
        review.id: sum(
            _overlap_days(start, end, review.period_start, review.period_end)
            for start, end in by_user[review.user_id]
        )
        for review in reviews
    }


def review_leave_days(serializer, review) -> int:
    """
    leave_days for one review inside a serializer: read from the batched
    context['leave_days'] when the view supplied it, otherwise one query.
    """
    batched = serializer.context.get('leave_days')
    if batched is not None:
        return batched.get(review.id, 0)
    return approved_leave_days(review.user_id, review.period_start, review.period_end)
