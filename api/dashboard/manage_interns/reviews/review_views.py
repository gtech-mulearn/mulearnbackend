from datetime import timedelta
import uuid

from django.db import transaction
from django.utils.timezone import now
from rest_framework.views import APIView

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternSubmissionStatus, InternGuildStatus, InternHashtag
from db.intern import InternDailyTimesheet, UserInternGuildLink
from db.task import KarmaActivityLog, TaskList, Wallet
from db.achievement import UserStreak


class InternTimesheetReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
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
                
                # Use entry_date to determine consecutiveness logically
                if streak.last_active:
                    if streak.last_active == timesheet.entry_date - timedelta(days=1):
                        streak.current_streak += 1
                    elif streak.last_active == timesheet.entry_date:
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
                timesheet.karma_awarded = karma_to_award
                
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
                    
                    wallet, _ = Wallet.objects.get_or_create(user_id=user_id)
                    wallet.karma += karma_to_award
                    wallet.save()

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
                        wallet, _ = Wallet.objects.get_or_create(user_id=user_id)
                        wallet.karma += bonus_karma
                        wallet.save()
                        
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
                review.karma_awarded = karma_to_award
                
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
                    
                    wallet, _ = Wallet.objects.get_or_create(user_id=user_id)
                    wallet.karma += karma_to_award
                    wallet.save()
                    
                streak.save()

            elif action == "reject":
                review.status = InternSubmissionStatus.REJECTED.value
                review.reviewed_by_id = admin_id
                review.reviewed_at = now()
                review.review_note = review_note
                
            review.save()
            return CustomResponse(general_message=f"Weekly review {action}ed successfully.").get_success_response()
