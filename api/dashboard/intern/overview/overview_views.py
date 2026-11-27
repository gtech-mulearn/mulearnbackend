from django.db.models import Min, Sum
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.intern_permissions import current_membership, members_only
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.intern import InternTask, UserInternTeamLink
from db.task import KarmaActivityLog
from db.achievement import UserStreak

from api.dashboard.intern.leaderboard.scoring import (
    COMPLEXITY_WEIGHT, DAILY_STREAK_TYPE, WEEKLY_STREAK_TYPE, ranked_members, scores_for,
)


class InternOverviewStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "The intern's overview: current team (`guild` is deprecated: the team name), status, "
            "first join date, intern karma, daily and weekly streaks, completed tasks and the leaderboard score (timesheets x 25 + verified task "
            "karma x complexity weight). total_interns counts current team members."
        ),
        responses={200: OpenApiResponse(description="Intern status overview data.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        link = current_membership(user_id)
        if not link:
            return CustomResponse(general_message="Not an intern.").get_failure_response()

        streaks = {
            streak.streak_type: streak
            for streak in UserStreak.objects.filter(
                user_id=user_id, streak_type__in=[DAILY_STREAK_TYPE, WEEKLY_STREAK_TYPE],
            )
        }
        daily_streak = streaks.get(DAILY_STREAK_TYPE)
        weekly_streak = streaks.get(WEEKLY_STREAK_TYPE)
        total_intern_karma = (
            KarmaActivityLog.objects.filter(user_id=user_id, task__hashtag__startswith='#intern-')
            .aggregate(Sum('karma'))['karma__sum'] or 0
        )
        completed = list(
            InternTask.objects.filter(assigned_to_id=user_id, status='COMPLETED').values_list('complexity', flat=True)
        )
        first_joined = UserInternTeamLink.objects.filter(user_id=user_id).aggregate(first=Min('created_at'))['first']

        data = {
            "team": {"id": link.team.id, "name": link.team.name, "code": link.team.code},
            # Deprecated: the old guild field, now the team name. Kept for existing clients.
            "guild": link.team.name,
            "status": link.intern_status,
            "join_date": first_joined.date().isoformat() if first_joined else None,
            "total_intern_karma": total_intern_karma,
            "daily_streak": daily_streak.current_streak if daily_streak else 0,
            "longest_daily_streak": daily_streak.longest_streak if daily_streak else 0,
            "weekly_streak": weekly_streak.current_streak if weekly_streak else 0,
            "longest_weekly_streak": weekly_streak.longest_streak if weekly_streak else 0,
            "completed_tasks": len(completed),
            "complexity_score": sum(COMPLEXITY_WEIGHT.get(c, 1) for c in completed),
            "score": scores_for([user_id])[user_id],
            "total_interns": members_only(UserInternTeamLink.objects.all()).count(),
        }
        return CustomResponse(response=data).get_success_response()


class InternOverviewActivityAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve paginated intern karma activity log.",
        responses={200: OpenApiResponse(description="List of intern karma activity entries.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        logs = KarmaActivityLog.objects.filter(
            user_id=user_id, 
            task__hashtag__startswith='#intern-'
        ).select_related('task').order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            logs, request,
            ['task__title'],
            {'created_at': 'created_at'}
        )
        
        data = [{
            "id": log.id,
            "task_title": log.task.title,
            "karma": log.karma,
            "created_at": log.created_at
        } for log in paginated_queryset.get("queryset")]
        
        return CustomResponse(
            response={
                "data": data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()


class InternOverviewLeaderboardTopAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="The top 3 of the intern leaderboard (same ranking as intern/leaderboard/).",
        responses={200: OpenApiResponse(description="Top 3 intern leaderboard entries.")},
    )
    def get(self, request):
        top_three = [
            {key: row[key] for key in ("user_id", "full_name", "team", "guild", "score", "rank")}
            for row in ranked_members()[:3]
        ]
        return CustomResponse(response=top_three).get_success_response()
