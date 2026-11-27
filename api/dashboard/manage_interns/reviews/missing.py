"""
Who didn't submit: daily timesheets and monthly reviews.

Every membership row (current or ended) counts for the days its tenure covers,
join_date..end_date, so former members are checked for the time they were in
the team and gaps between stints aren't. Each check is per person: on a reassign
day (old row ends today, new row starts today) the person is expected once, under
the row that started last.

Leave doesn't hide anyone: each missing entry says whether approved leave covers
the day (daily) or how many approved leave days fall in the month (monthly).

Queries are batched over the whole range (memberships, then timesheets or reviews,
then approved leave), so the cost doesn't grow with the number of days.
"""
from collections import defaultdict
from datetime import timedelta

from db.intern import InternDailyTimesheet, InternLeaveRequest, InternMonthlyReview, UserInternTeamLink
from utils.intern_permissions import caller_team_id, is_admin
from utils.types import InternLeaveStatus, InternSubmissionStatus

SUBMITTED_REVIEW = [InternSubmissionStatus.PENDING.value, InternSubmissionStatus.APPROVED.value]


def scoped_rows(request, start, end):
    """
    (rows, team_id): every membership row, from every team, of each person who has a
    row in the caller's team scope overlapping start..end, plus the team the results
    must be limited to (None = all). All of a person's rows are needed so the right
    one can be picked for a day before filtering by team.
    """
    overlapping = UserInternTeamLink.objects.filter(join_date__lte=end, end_date__gte=start)
    if is_admin(request):
        team_id = request.query_params.get('team_id') or None
    else:
        team_id = caller_team_id(request)
        if not team_id:
            return [], None
    if team_id:
        overlapping = overlapping.filter(
            user_id__in=UserInternTeamLink.objects.filter(
                team_id=team_id, join_date__lte=end, end_date__gte=start,
            ).values('user_id')
        )
    return list(overlapping.select_related('user', 'team')), team_id


def _row_for(rows, day_start, day_end):
    """Per person: the row overlapping day_start..day_end that started last."""
    best = {}
    for row in rows:
        if row.join_date <= day_end and row.end_date >= day_start:
            current = best.get(row.user_id)
            if current is None or (row.join_date, row.is_current) > (current.join_date, current.is_current):
                best[row.user_id] = row
    return best


def _approved_leave(user_ids, start, end):
    leave = defaultdict(list)
    for user_id, s, e, kind in InternLeaveRequest.objects.filter(
        user_id__in=user_ids, status=InternLeaveStatus.APPROVED.value, start_date__lte=end, end_date__gte=start,
    ).values_list('user_id', 'start_date', 'end_date', 'leave_type'):
        leave[user_id].append((s, e, kind))
    return leave


def _person(row):
    return {
        "user": row.user_id,
        "full_name": row.user.full_name,
        "muid": row.user.muid,
        "team": {"id": row.team.id, "name": row.team.name, "code": row.team.code},
        "status": row.intern_status,
    }


def daily_missing(request, start, end):
    """[(day, row, leave_type or None)] for every person with no timesheet on a day in start..end."""
    rows, team_id = scoped_rows(request, start, end)
    user_ids = {row.user_id for row in rows}
    submitted = set(
        InternDailyTimesheet.objects.filter(user_id__in=user_ids, entry_date__range=(start, end))
        .values_list('user_id', 'entry_date')
    )
    leave = _approved_leave(user_ids, start, end)
    out = []
    day = start
    while day <= end:
        for user_id, row in _row_for(rows, day, day).items():
            if (user_id, day) in submitted or (team_id and row.team_id != team_id):
                continue
            leave_type = next((kind for s, e, kind in leave[user_id] if s <= day <= e), None)
            out.append((day, row, leave_type))
        day += timedelta(days=1)
    return out


def monthly_missing(request, months):
    """
    [(window, row, leave_days)] for every person with no PENDING or APPROVED review
    for a month in `months` (a list of MonthlyReviewWindow). Someone whose tenure
    ends before that month's window closes is left out: they leave during (or
    before) the window, and can't submit once their tenure has ended.
    """
    if not months:
        return []
    start, end = months[0].period_start, months[-1].period_end
    rows, team_id = scoped_rows(request, start, end)
    user_ids = {row.user_id for row in rows}
    submitted = set(
        InternMonthlyReview.objects.filter(
            user_id__in=user_ids, status__in=SUBMITTED_REVIEW,
            period_start__gte=start, period_end__lte=end,
        ).values_list('user_id', 'year', 'month')
    )
    leave = _approved_leave(user_ids, start, end)
    out = []
    for window in months:
        for user_id, row in _row_for(rows, window.period_start, window.period_end).items():
            if (user_id, window.year, window.month) in submitted or row.end_date < window.closes_on:
                continue
            if team_id and row.team_id != team_id:
                continue
            days = sum(
                max(0, (min(e, window.period_end) - max(s, window.period_start)).days + 1)
                for s, e, _ in leave[user_id]
            )
            out.append((window, row, days))
    return out


def person(row):
    return _person(row)
