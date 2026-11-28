"""
Intern leaderboard score, shared by intern/overview/ and intern/leaderboard/.

    score = timesheets x 25
          + sum over verified tasks of karma_awarded x complexity weight

Counted over all time. Ranked: current team members who hold an intern role and
are inside their tenure and ACTIVE or ON_LEAVE (not INACTIVE, not upcoming or finished). Every query is batched, so the
cost doesn't grow with the number of interns beyond the rows themselves.
"""
from django.db.models import Count

from db.achievement import UserStreak
from db.intern import InternDailyTimesheet, InternTask, UserInternTeamLink
from utils.intern_permissions import working_members

TIMESHEET_POINTS = 25
COMPLEXITY_WEIGHT = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}
DAILY_STREAK_TYPE = 'intern_timesheet'
WEEKLY_STREAK_TYPE = 'intern_weekly_review'


def scores_for(user_ids):
    """{user_id: score} for the given people (0 for anyone with nothing counted)."""
    user_ids = list(user_ids)
    timesheets = dict(
        InternDailyTimesheet.objects.filter(user_id__in=user_ids)
        .values('user_id').annotate(total=Count('id')).values_list('user_id', 'total')
    )
    task_points = {}
    for user_id, karma, complexity in (
        InternTask.objects.filter(assigned_to_id__in=user_ids, is_verified=True)
        .values_list('assigned_to_id', 'karma_awarded', 'complexity')
    ):
        task_points[user_id] = task_points.get(user_id, 0) + (karma or 0) * COMPLEXITY_WEIGHT.get(complexity, 1)
    return {
        user_id: timesheets.get(user_id, 0) * TIMESHEET_POINTS + task_points.get(user_id, 0)
        for user_id in user_ids
    }


def ranked_members():
    """
    Every ranked member, best first: a list of dicts with user_id, full_name,
    team ({id, name, code}), guild (deprecated: the team name), score,
    daily_streak, weekly_streak and rank. Ties keep a stable
    order by name.
    """
    links = list(
        working_members(UserInternTeamLink.objects.select_related('user', 'team'))
        .order_by('user__full_name')
    )
    user_ids = [link.user_id for link in links]
    scores = scores_for(user_ids)
    streaks = {
        (user_id, kind): current
        for user_id, kind, current in UserStreak.objects.filter(
            user_id__in=user_ids, streak_type__in=[DAILY_STREAK_TYPE, WEEKLY_STREAK_TYPE],
        ).values_list('user_id', 'streak_type', 'current_streak')
    }
    rows = [
        {
            "user_id": link.user_id,
            "full_name": link.user.full_name,
            "team": {"id": link.team.id, "name": link.team.name, "code": link.team.code},
            # Deprecated: the old guild field, now the team name. Kept for existing clients.
            "guild": link.team.name,
            "score": scores.get(link.user_id, 0),
            "daily_streak": streaks.get((link.user_id, DAILY_STREAK_TYPE), 0),
            "weekly_streak": streaks.get((link.user_id, WEEKLY_STREAK_TYPE), 0),
        }
        for link in links
    ]
    rows.sort(key=lambda row: row["score"], reverse=True)  # stable: ties stay in name order
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows
