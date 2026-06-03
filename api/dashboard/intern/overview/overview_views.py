from rest_framework.views import APIView
from django.db.models import Sum

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternLeaderboardWeights
from utils.utils import CommonUtils
from db.intern import UserInternGuildLink, InternTask
from db.task import KarmaActivityLog
from db.achievement import UserStreak

class InternOverviewStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()
        
        if not guild_link:
            return CustomResponse(general_message="Not an intern.").get_failure_response()
            
        daily_streak = UserStreak.objects.filter(user_id=user_id, streak_type='intern_timesheet').first()
        weekly_streak = UserStreak.objects.filter(user_id=user_id, streak_type='intern_weekly_review').first()
        
        intern_karma_logs = KarmaActivityLog.objects.filter(user_id=user_id, task__hashtag__startswith='#intern-')
        total_intern_karma = intern_karma_logs.aggregate(Sum('karma'))['karma__sum'] or 0
        
        completed_tasks = InternTask.objects.filter(assigned_to_id=user_id, status='COMPLETED').count()
        
        tasks = InternTask.objects.filter(assigned_to_id=user_id, status='COMPLETED')
        complexity_map = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}
        complexity_score = sum([complexity_map.get(t.complexity, 1) for t in tasks])
        
        d_streak_val = daily_streak.current_streak if daily_streak else 0
        w_streak_val = weekly_streak.current_streak if weekly_streak else 0
        
        score = (total_intern_karma * InternLeaderboardWeights.KARMA_MULTIPLIER +
                 d_streak_val * InternLeaderboardWeights.DAILY_STREAK_MULTIPLIER +
                 w_streak_val * InternLeaderboardWeights.WEEKLY_STREAK_MULTIPLIER +
                 completed_tasks * InternLeaderboardWeights.COMPLETED_TASKS_MULTIPLIER +
                 complexity_score * InternLeaderboardWeights.COMPLEXITY_SCORE_MULTIPLIER)
        
        data = {
            "guild": guild_link.guild,
            "status": guild_link.status,
            "total_intern_karma": total_intern_karma,
            "daily_streak": d_streak_val,
            "weekly_streak": w_streak_val,
            "completed_tasks": completed_tasks,
            "complexity_score": complexity_score,
            "score": score
        }
        return CustomResponse(response=data).get_success_response()


class InternOverviewActivityAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        logs = KarmaActivityLog.objects.filter(
            user_id=user_id, 
            task__type__title='Intern Task'
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
    def get(self, request):
        # Returning empty for now until Phase 8 Leaderboard logic is implemented,
        # which will be extracted to a shared service to provide top 3 easily.
        return CustomResponse(response=[]).get_success_response()
