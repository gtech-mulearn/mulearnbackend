from rest_framework.views import APIView
from django.db.models import Sum, Count
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternLeaderboardWeights, InternGuildStatus
from db.intern import UserInternGuildLink, InternTask, InternDailyTimesheet, InternWeeklyReview
from db.task import KarmaActivityLog
from db.achievement import UserStreak

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
            
        approved_daily_timesheets = InternDailyTimesheet.objects.filter(user_id__in=intern_user_ids, status='APPROVED').values('user_id').annotate(total=Count('id'))
        daily_ts_counts = {item['user_id']: item['total'] for item in approved_daily_timesheets}
        
        approved_weekly_reviews = InternWeeklyReview.objects.filter(user_id__in=intern_user_ids, status='APPROVED').values('user_id').annotate(total=Count('id'))
        weekly_rv_counts = {item['user_id']: item['total'] for item in approved_weekly_reviews}
        
        verified_tasks = InternTask.objects.filter(assigned_to_id__in=intern_user_ids, is_verified=True)
        verified_tasks_by_user = {}
        for t in verified_tasks:
            verified_tasks_by_user.setdefault(t.assigned_to_id, []).append(t)

            
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
            
            approved_daily_timesheets_count = daily_ts_counts.get(user_id, 0)
            approved_weekly_reviews_count = weekly_rv_counts.get(user_id, 0)
            
            user_verified_tasks = verified_tasks_by_user.get(user_id, [])
            verified_intern_tasks_score = sum(
                [t.karma_awarded * complexity_map.get(t.complexity, 1) for t in user_verified_tasks]
            )
            
            score = (
                approved_daily_timesheets_count * 25 +
                approved_weekly_reviews_count * 50 +
                verified_intern_tasks_score
            )
            
            leaderboard_data.append({
                "user_id": user_id,
                "full_name": intern.user.full_name,
                "guild": intern.guild,
                "score": score
            })
            
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
            
        approved_daily_timesheets = InternDailyTimesheet.objects.filter(user_id__in=intern_user_ids, status='APPROVED').values('user_id').annotate(total=Count('id'))
        daily_ts_counts = {item['user_id']: item['total'] for item in approved_daily_timesheets}
        
        approved_weekly_reviews = InternWeeklyReview.objects.filter(user_id__in=intern_user_ids, status='APPROVED').values('user_id').annotate(total=Count('id'))
        weekly_rv_counts = {item['user_id']: item['total'] for item in approved_weekly_reviews}
        
        verified_tasks = InternTask.objects.filter(assigned_to_id__in=intern_user_ids, is_verified=True)
        verified_tasks_by_user = {}
        for t in verified_tasks:
            verified_tasks_by_user.setdefault(t.assigned_to_id, []).append(t)
            
        leaderboard_data = []
        for intern in interns:
            uid = intern.user_id
            
            d_streak_val = daily_streaks.get(uid, 0)
            w_streak_val = weekly_streaks.get(uid, 0)
            total_intern_karma = karma_dict.get(uid, 0)
            
            user_tasks = tasks_by_user.get(uid, [])
            completed_count = len(user_tasks)
            
            complexity_map = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}
            complexity_score = sum([complexity_map.get(t.complexity, 1) for t in user_tasks])
            
            approved_daily_timesheets_count = daily_ts_counts.get(uid, 0)
            approved_weekly_reviews_count = weekly_rv_counts.get(uid, 0)
            
            user_verified_tasks = verified_tasks_by_user.get(uid, [])
            verified_intern_tasks_score = sum(
                [t.karma_awarded * complexity_map.get(t.complexity, 1) for t in user_verified_tasks]
            )
            
            score = (
                approved_daily_timesheets_count * 25 +
                approved_weekly_reviews_count * 50 +
                verified_intern_tasks_score
            )
            
            leaderboard_data.append({
                "user_id": uid,
                "score": score
            })
            
        leaderboard_data.sort(key=lambda x: x['score'], reverse=True)
        
        rank = -1
        score = 0
        for i, entry in enumerate(leaderboard_data):
            if entry['user_id'] == user_id:
                rank = i + 1
                score = entry['score']
                break
                
        if rank == -1:
            return CustomResponse(general_message="Not found in leaderboard.").get_failure_response()
            
        return CustomResponse(response={"rank": rank, "score": score}).get_success_response()
