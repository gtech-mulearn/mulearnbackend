from rest_framework.views import APIView
from django.db.models import Sum, Count
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternLeaderboardWeights, InternGuildStatus, COUNTED_TIMESHEET_STATUSES
from db.intern import UserInternGuildLink, InternTask, InternDailyTimesheet, InternWeeklyReview
from db.achievement import UserStreak

COMPLEXITY_WEIGHT = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}


def intern_scores(user_ids):
    """
    {user_id: leaderboard score} for these interns, in three grouped queries:
    counted daily timesheets (COUNTED_TIMESHEET_STATUSES) x 25 + approved
    weekly reviews x 50 + the sum of
    karma_awarded x complexity weight over verified intern tasks. Shared by
    the leaderboard, "me" and overview top-3 views.
    """
    user_ids = list(user_ids)
    daily = dict(
        InternDailyTimesheet.objects.filter(user_id__in=user_ids, status__in=COUNTED_TIMESHEET_STATUSES)
        .values('user_id').annotate(total=Count('id')).values_list('user_id', 'total')
    )
    weekly = dict(
        InternWeeklyReview.objects.filter(user_id__in=user_ids, status='APPROVED')
        .values('user_id').annotate(total=Count('id')).values_list('user_id', 'total')
    )
    tasks = {}
    for assigned_to_id, karma_awarded, complexity in InternTask.objects.filter(
        assigned_to_id__in=user_ids, is_verified=True
    ).values_list('assigned_to_id', 'karma_awarded', 'complexity'):
        tasks[assigned_to_id] = tasks.get(assigned_to_id, 0) + karma_awarded * COMPLEXITY_WEIGHT.get(complexity, 1)
    return {
        user_id: daily.get(user_id, 0) * 25 + weekly.get(user_id, 0) * 50 + tasks.get(user_id, 0)
        for user_id in user_ids
    }


def intern_streaks(user_ids):
    """({user_id: daily streak}, {user_id: weekly streak}) in one query."""
    streaks = UserStreak.objects.filter(user_id__in=list(user_ids)).only('user_id', 'streak_type', 'current_streak')
    daily = {s.user_id: s.current_streak for s in streaks if s.streak_type == 'intern_timesheet'}
    weekly = {s.user_id: s.current_streak for s in streaks if s.streak_type == 'intern_weekly_review'}
    return daily, weekly


class InternLeaderboardAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value, RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve the full paginated intern leaderboard with scores and ranks.",
        responses={200: OpenApiResponse(description="Paginated leaderboard data with rank and score.")},
    )
    def get(self, request):
        interns = UserInternGuildLink.objects.filter(
            status__in=[
                InternGuildStatus.ACTIVE.value,
                InternGuildStatus.AT_RISK.value,
                InternGuildStatus.ON_LEAVE.value,
            ]
        ).select_related('user')
        
        intern_user_ids = [intern.user_id for intern in interns]
        # (Intern karma and completed-task lists were also loaded here but
        # never used in the response; dropped.)
        daily_streaks, weekly_streaks = intern_streaks(intern_user_ids)
        scores = intern_scores(intern_user_ids)

        leaderboard_data = [
            {
                "user_id": intern.user_id,
                "full_name": intern.user.full_name,
                "guild": intern.guild,
                "score": scores[intern.user_id],
                "daily_streak": daily_streaks.get(intern.user_id, 0),
                "weekly_streak": weekly_streaks.get(intern.user_id, 0),
            }
            for intern in interns
        ]
            
        leaderboard_data.sort(key=lambda x: x['score'], reverse=True)
        
        for i, entry in enumerate(leaderboard_data):
            entry['rank'] = i + 1
            
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_data = leaderboard_data[start:end]
        
        return CustomResponse(
            response={
                "data": paginated_data,
                "pagination": {
                    "count": len(leaderboard_data),
                    "totalPages": (len(leaderboard_data) + page_size - 1) // page_size,
                    "isNext": end < len(leaderboard_data),
                    "isPrev": start > 0,
                    "nextPage": page + 1 if end < len(leaderboard_data) else None
                }
            }
        ).get_success_response()

class InternLeaderboardMeAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve the current intern's rank and score on the leaderboard.",
        responses={200: OpenApiResponse(description="Intern rank and score.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        interns = UserInternGuildLink.objects.filter(
            status__in=[
                InternGuildStatus.ACTIVE.value,
                InternGuildStatus.AT_RISK.value,
                InternGuildStatus.ON_LEAVE.value,
            ]
        )
        
        intern_user_ids = [intern.user_id for intern in interns]
        daily_streaks, weekly_streaks = intern_streaks(intern_user_ids)
        scores = intern_scores(intern_user_ids)

        leaderboard_data = [
            {
                "user_id": intern.user_id,
                "score": scores[intern.user_id],
                "daily_streak": daily_streaks.get(intern.user_id, 0),
                "weekly_streak": weekly_streaks.get(intern.user_id, 0),
            }
            for intern in interns
        ]
            
        leaderboard_data.sort(key=lambda x: x['score'], reverse=True)
        
        rank = -1
        score = 0
        daily_streak = 0
        weekly_streak = 0
        for i, entry in enumerate(leaderboard_data):
            if entry['user_id'] == user_id:
                rank = i + 1
                score = entry['score']
                daily_streak = entry['daily_streak']
                weekly_streak = entry['weekly_streak']
                break
                
        if rank == -1:
            return CustomResponse(general_message="Not found in leaderboard.").get_failure_response()
            
        return CustomResponse(response={"rank": rank, "score": score, "daily_streak": daily_streak, "weekly_streak": weekly_streak}).get_success_response()
