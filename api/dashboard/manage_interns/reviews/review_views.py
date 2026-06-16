from datetime import timedelta
import uuid

from django.db import transaction
from django.utils.timezone import now
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternSubmissionStatus, InternGuildStatus, InternHashtag
from db.intern import InternDailyTimesheet, UserInternGuildLink, InternWeeklyReview
from db.task import KarmaActivityLog, TaskList, Wallet
from db.achievement import UserStreak
from utils.utils import CommonUtils
from .serializers import ManageInternWeeklyReviewSerializer, ManageInternTimesheetSerializer


class InternTimesheetReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve a timesheet for review.",
        responses={200: ManageInternTimesheetSerializer},
    )
    def get(self, request, timesheet_id):
        timesheet = InternDailyTimesheet.objects.filter(id=timesheet_id).first()
        if not timesheet:
            return CustomResponse(general_message="Timesheet not found.").get_failure_response()
        serializer = ManageInternTimesheetSerializer(timesheet)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Approve or reject a timesheet.",
        responses={200: OpenApiResponse(description="Timesheet reviewed successfully.")},
    )
    def patch(self, request, timesheet_id):
        admin_id = JWTUtils.fetch_user_id(request)
        action = request.data.get("action")
        review_note = request.data.get("review_note")
        
        if action not in ["approve", "reject"]:
            return CustomResponse(general_message="Invalid action. Must be 'approve' or 'reject'.").get_failure_response()
            
        timesheet = InternDailyTimesheet.objects.filter(id=timesheet_id, status=InternSubmissionStatus.PENDING.value).first()
        if not timesheet:
            return CustomResponse(general_message="Pending timesheet not found.").get_failure_response()
            
        with transaction.atomic():
            if action == "approve":
                timesheet.status = InternSubmissionStatus.APPROVED.value
                timesheet.reviewed_by_id = admin_id
                timesheet.reviewed_at = now()
                
                user_id = timesheet.user_id
                streak, _ = UserStreak.objects.get_or_create(user_id=user_id, streak_type='intern_timesheet')
                
                # Use entry_date to determine consecutiveness logically (skip weekends)
                if streak.last_active:
                    days_diff = (timesheet.entry_date - streak.last_active).days
                    is_consecutive = False
                    
                    if days_diff == 1:
                        is_consecutive = True
                    elif days_diff == 3 and timesheet.entry_date.weekday() == 0 and streak.last_active.weekday() == 4:
                        # Friday to Monday
                        is_consecutive = True
                        
                    if is_consecutive:
                        streak.current_streak += 1
                    elif days_diff == 0:
                        pass # Same day, no increment
                    else:
                        streak.current_streak = 1
                else:
                    streak.current_streak = 1
                    
                streak.longest_streak = max(streak.current_streak, streak.longest_streak)
                streak.last_active = timesheet.entry_date
                
                base_karma = InternHashtag.DAILY_LOG_KARMA.value
                multiplier = 1.0
                if streak.current_streak >= 30:
                    multiplier = 2.0
                elif streak.current_streak >= 14:
                    multiplier = 1.5
                elif streak.current_streak >= 7:
                    multiplier = 1.2
                    
                karma_to_award = int(base_karma * multiplier)
                
                task_list = TaskList.objects.filter(hashtag=InternHashtag.DAILY_LOG_HASHTAG.value).first()
                if task_list:
                    KarmaActivityLog.objects.create(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        task=task_list,
                        karma=karma_to_award,
                        appraiser_approved=True,
                        updated_by_id=admin_id,
                        updated_at=now(),
                        created_by_id=admin_id,
                        created_at=now()
                    )
                    
                    from django.db.models import F
                    wallet, _ = Wallet.objects.get_or_create(user_id=user_id, defaults={'created_by_id': admin_id, 'updated_by_id': admin_id})
                    Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + karma_to_award)

                milestones = {
                    7: (InternHashtag.STREAK_7_HASHTAG.value, InternHashtag.STREAK_7_KARMA.value),
                    14: (InternHashtag.STREAK_14_HASHTAG.value, InternHashtag.STREAK_14_KARMA.value),
                    30: (InternHashtag.STREAK_30_HASHTAG.value, InternHashtag.STREAK_30_KARMA.value),
                    60: (InternHashtag.STREAK_60_HASHTAG.value, InternHashtag.STREAK_60_KARMA.value),
                    90: (InternHashtag.STREAK_90_HASHTAG.value, InternHashtag.STREAK_90_KARMA.value),
                }
                
                if streak.current_streak in milestones:
                    hashtag, bonus_karma = milestones[streak.current_streak]
                    milestone_task = TaskList.objects.filter(hashtag=hashtag).first()
                    if milestone_task:
                        KarmaActivityLog.objects.create(
                            id=str(uuid.uuid4()),
                            user_id=user_id,
                            task=milestone_task,
                            karma=bonus_karma,
                            appraiser_approved=True,
                            updated_by_id=admin_id,
                            updated_at=now(),
                            created_by_id=admin_id,
                            created_at=now()
                        )
                        from django.db.models import F
                        wallet, _ = Wallet.objects.get_or_create(user_id=user_id, defaults={'created_by_id': admin_id, 'updated_by_id': admin_id})
                        Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + bonus_karma)
                        
                streak.save()
                
                guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()
                if guild_link and guild_link.status == InternGuildStatus.AT_RISK.value:
                    guild_link.status = InternGuildStatus.ACTIVE.value
                    guild_link.save()

            elif action == "reject":
                timesheet.status = InternSubmissionStatus.REJECTED.value
                timesheet.reviewed_by_id = admin_id
                timesheet.reviewed_at = now()
                timesheet.review_note = review_note
                
            timesheet.save()
            return CustomResponse(general_message=f"Timesheet {action}ed successfully.").get_success_response()

class InternWeeklyReviewReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve a weekly review for detail.",
        responses={200: ManageInternWeeklyReviewSerializer},
    )
    def get(self, request, review_id):
        review = InternWeeklyReview.objects.filter(id=review_id).first()
        if not review:
            return CustomResponse(general_message="Weekly review not found.").get_failure_response()
        serializer = ManageInternWeeklyReviewSerializer(review)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Approve or reject a weekly review.",
        responses={200: OpenApiResponse(description="Weekly review reviewed successfully.")},
    )
    def patch(self, request, review_id):
        admin_id = JWTUtils.fetch_user_id(request)
        action = request.data.get("action")
        review_note = request.data.get("review_note")
        
        if action not in ["approve", "reject"]:
            return CustomResponse(general_message="Invalid action. Must be 'approve' or 'reject'.").get_failure_response()
            
        review = InternWeeklyReview.objects.filter(id=review_id, status=InternSubmissionStatus.PENDING.value).first()
        if not review:
            return CustomResponse(general_message="Pending weekly review not found.").get_failure_response()
            
        with transaction.atomic():
            if action == "approve":
                review.status = InternSubmissionStatus.APPROVED.value
                review.reviewed_by_id = admin_id
                review.reviewed_at = now()
                
                user_id = review.user_id
                
                streak, _ = UserStreak.objects.get_or_create(user_id=user_id, streak_type='intern_weekly_review')
                
                if review.is_late:
                    streak.current_streak = 0
                else:
                    if streak.last_active:
                        if streak.last_active == review.week_start_date - timedelta(days=7):
                            streak.current_streak += 1
                        elif streak.last_active == review.week_start_date:
                            pass
                        else:
                            streak.current_streak = 1
                    else:
                        streak.current_streak = 1
                        
                streak.longest_streak = max(streak.current_streak, streak.longest_streak)
                streak.last_active = review.week_start_date
                
                karma_to_award = InternHashtag.WEEKLY_REVIEW_KARMA.value
                
                task_list = TaskList.objects.filter(hashtag=InternHashtag.WEEKLY_REVIEW_HASHTAG.value).first()
                if task_list:
                    KarmaActivityLog.objects.create(
                        id=str(uuid.uuid4()),
                        user_id=user_id,
                        task=task_list,
                        karma=karma_to_award,
                        appraiser_approved=True,
                        updated_by_id=admin_id,
                        updated_at=now(),
                        created_by_id=admin_id,
                        created_at=now()
                    )
                    
                    from django.db.models import F
                    wallet, _ = Wallet.objects.get_or_create(user_id=user_id, defaults={'created_by_id': admin_id, 'updated_by_id': admin_id})
                    Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + karma_to_award)
                    
                streak.save()

            elif action == "reject":
                review.status = InternSubmissionStatus.REJECTED.value
                review.reviewed_by_id = admin_id
                review.reviewed_at = now()
                review.review_note = review_note
                
            review.save()
            return CustomResponse(general_message=f"Weekly review {action}ed successfully.").get_success_response()


class InternWeeklyReviewListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="List weekly reviews with filters.",
        responses={200: ManageInternWeeklyReviewSerializer(many=True)},
    )
    def get(self, request):
        reviews = InternWeeklyReview.objects.all().order_by('-created_at')
        
        status = request.query_params.get('status')
        if status:
            reviews = reviews.filter(status=status)
            
        paginated_queryset = CommonUtils.get_paginated_queryset(
            reviews, request,
            ['user__full_name', 'status', 'team'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = ManageInternWeeklyReviewSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()


class InternTimesheetListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="List timesheets with filters.",
        responses={200: ManageInternTimesheetSerializer(many=True)},
    )
    def get(self, request):
        timesheets = InternDailyTimesheet.objects.all().order_by('-created_at')
        
        status = request.query_params.get('status')
        if status:
            timesheets = timesheets.filter(status=status)
            
        paginated_queryset = CommonUtils.get_paginated_queryset(
            timesheets, request,
            ['user__full_name', 'status', 'category'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = ManageInternTimesheetSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()
