from rest_framework.views import APIView
from django.db.models import Sum
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternLeaderboardWeights, InternGuildStatus
from utils.utils import CommonUtils
from db.intern import UserInternGuildLink, InternTask
from db.task import KarmaActivityLog
from db.achievement import UserStreak

class InternOverviewStatusAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve intern overview status including karma, streaks, tasks, and score.",
        responses={200: OpenApiResponse(description="Intern status overview data.")},
    )
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
        description="Retrieve the top 3 interns on the leaderboard.",
        responses={200: OpenApiResponse(description="Top 3 intern leaderboard entries.")},
    )
    def get(self, request):
        interns = UserInternGuildLink.objects.filter(
            status__in=[InternGuildStatus.ACTIVE.value, InternGuildStatus.AT_RISK.value]
        ).select_related('user')
        
        intern_user_ids = [intern.user_id for intern in interns]
        
        streaks = UserStreak.objects.filter(user_id__in=intern_user_ids)
        daily_streaks = {s.user_id: s.current_streak for s in streaks if s.streak_type == 'intern_timesheet'}
        weekly_streaks = {s.user_id: s.current_streak for s in streaks if s.streak_type == 'intern_weekly_review'}
        
        karma_logs = KarmaActivityLog.objects.filter(user_id__in=intern_user_ids, task__hashtag__startswith='#intern-')
        karma_by_user = karma_logs.values('user_id').annotate(total=Sum('karma'))
        karma_dict = {item['user_id']: item['total'] for item in karma_by_user}
        
        completed_tasks = InternTask.objects.filter(assigned_to_id__in=intern_user_ids, status='COMPLETED')
        tasks_by_user = {}
        for t in completed_tasks:
            tasks_by_user.setdefault(t.assigned_to_id, []).append(t)
            
        leaderboard_data = []
        for intern in interns:
            user_id = intern.user_id
            
            d_streak_val = daily_streaks.get(user_id, 0)
            w_streak_val = weekly_streaks.get(user_id, 0)
            total_intern_karma = karma_dict.get(user_id, 0)
            
            user_tasks = tasks_by_user.get(user_id, [])
            completed_count = len(user_tasks)
            
            complexity_map = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}
            complexity_score = sum([complexity_map.get(t.complexity, 1) for t in user_tasks])
            
            score = (total_intern_karma * InternLeaderboardWeights.KARMA_MULTIPLIER +
                     d_streak_val * InternLeaderboardWeights.DAILY_STREAK_MULTIPLIER +
                     w_streak_val * InternLeaderboardWeights.WEEKLY_STREAK_MULTIPLIER +
                     completed_count * InternLeaderboardWeights.COMPLETED_TASKS_MULTIPLIER +
                     complexity_score * InternLeaderboardWeights.COMPLEXITY_SCORE_MULTIPLIER)
                     
            leaderboard_data.append({
                "user_id": user_id,
                "full_name": intern.user.full_name,
                "guild": intern.guild,
                "score": score
            })
            
        leaderboard_data.sort(key=lambda x: x['score'], reverse=True)
        top_three = leaderboard_data[:3]
        for i, entry in enumerate(top_three):
            entry['rank'] = i + 1
            
        return CustomResponse(response=top_three).get_success_response()


class InternGuildsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value, RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve all available intern guilds.",
        responses={200: OpenApiResponse(description="List of all intern guild values.")},
    )
    def get(self, request):
        from utils.types import InternGuild
        guilds = InternGuild.get_all_values()
        return CustomResponse(response=guilds).get_success_response()
