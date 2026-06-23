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


# ============================================================================
# Streak Recalculation Helpers
# ============================================================================

def recalculate_intern_timesheet_streak(user_id: str) -> dict:
    """
    Recalculates the intern_timesheet streak from scratch by looking at the
    entire history of approved timesheets, sorted chronologically.

    This is order-independent: the result is identical regardless of the
    order the admin approved individual timesheets.

    Returns:
        dict with keys:
            - current_streak (int): The streak ending at the latest entry_date
            - longest_streak (int): The overall longest continuous streak
            - last_active (date | None): The most recent approved entry_date
            - milestone_hits (dict): {milestone_days: count_of_times_reached}
    """
    approved_dates = list(
        InternDailyTimesheet.objects.filter(
            user_id=user_id,
            status=InternSubmissionStatus.APPROVED.value,
        )
        .order_by('entry_date')
        .values_list('entry_date', flat=True)
        .distinct()  # Guard against duplicate approvals for the same date
    )

    if not approved_dates:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'last_active': None,
            'milestone_hits': {},
        }

    milestones = [7, 14, 30, 60, 90]
    milestone_hits = {m: 0 for m in milestones}

    current = 1
    longest = 1
    for m in milestones:
        if current >= m:
            milestone_hits[m] += 1

    for i in range(1, len(approved_dates)):
        prev = approved_dates[i - 1]
        curr = approved_dates[i]
        diff = (curr - prev).days

        # Consecutive: next calendar day, OR Friday→Monday (skipping weekend)
        is_consecutive = (
            diff == 1 or
            (diff == 3 and curr.weekday() == 0 and prev.weekday() == 4)
        )

        if is_consecutive:
            current += 1
        elif diff > 0:
            # Gap — streak resets
            current = 1
        # diff == 0 means duplicate date (already deduped, but just in case)

        longest = max(longest, current)
        for m in milestones:
            if current == m:
                milestone_hits[m] += 1

    return {
        'current_streak': current,
        'longest_streak': longest,
        'last_active': approved_dates[-1],
        'milestone_hits': milestone_hits,
    }


def recalculate_intern_weekly_streak(user_id: str) -> dict:
    """
    Recalculates the intern_weekly_review streak from scratch by looking at
    the entire history of approved weekly reviews, sorted chronologically.

    A late review (is_late=True) resets the streak to 0.

    Returns:
        dict with keys:
            - current_streak (int)
            - longest_streak (int)
            - last_active (date | None): The most recent approved week_start_date
    """
    approved_reviews = list(
        InternWeeklyReview.objects.filter(
            user_id=user_id,
            status=InternSubmissionStatus.APPROVED.value,
        )
        .order_by('week_start_date')
        .values('week_start_date', 'is_late')
    )

    if not approved_reviews:
        return {'current_streak': 0, 'longest_streak': 0, 'last_active': None}

    current = 0
    longest = 0
    last_week_start = None

    for review in approved_reviews:
        week_start = review['week_start_date']
        is_late = review['is_late']

        if is_late:
            current = 0
        elif last_week_start is None:
            current = 1
        elif (week_start - last_week_start).days == 7:
            current += 1
        elif week_start == last_week_start:
            pass  # Duplicate, ignore
        else:
            current = 1  # Gap

        longest = max(longest, current)
        last_week_start = week_start

    return {
        'current_streak': current,
        'longest_streak': longest,
        'last_active': last_week_start,
    }


def _award_missing_milestone_karma(user_id: str, admin_id: str, milestone_hits: dict, milestone_map: dict):
    """
    Awards milestone karma for any gaps between expected and actual hits.

    Uses "Expected vs Actual" logic:
      - expected_hits: how many times the streak crossed a milestone (from recalculation)
      - actual_hits:   how many times we already gave karma for that milestone

    Only awards the *difference*, so this is idempotent and safe to call on
    every approval regardless of order.

    Args:
        user_id:       The intern's user ID
        admin_id:      The admin performing the approval (used as created_by)
        milestone_hits: {milestone_days: expected_hit_count} from recalculate_*
        milestone_map:  {milestone_days: (hashtag, bonus_karma)}
    """
    from django.db.models import F

    for milestone_days, (hashtag, bonus_karma) in milestone_map.items():
        expected = milestone_hits.get(milestone_days, 0)
        if expected == 0:
            continue

        task_list = TaskList.objects.filter(hashtag=hashtag).first()
        if not task_list:
            continue

        actual = KarmaActivityLog.objects.filter(
            user_id=user_id,
            task=task_list,
            appraiser_approved=True,
        ).count()

        missing = expected - actual
        if missing <= 0:
            continue

        wallet, _ = Wallet.objects.get_or_create(
            user_id=user_id,
            defaults={'created_by_id': admin_id, 'updated_by_id': admin_id}
        )

        for _ in range(missing):
            KarmaActivityLog.objects.create(
                id=str(uuid.uuid4()),
                user_id=user_id,
                task=task_list,
                karma=bonus_karma,
                appraiser_approved=True,
                updated_by_id=admin_id,
                updated_at=now(),
                created_by_id=admin_id,
                created_at=now(),
            )
        Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + (bonus_karma * missing))


class InternTimesheetReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
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

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
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
                # Save the approved status first so the recalculation includes this timesheet
                timesheet.save()

                user_id = timesheet.user_id

                # --- Ground-up streak recalculation (order-independent) ---
                recalc = recalculate_intern_timesheet_streak(user_id)

                streak, _ = UserStreak.objects.get_or_create(user_id=user_id, streak_type='intern_timesheet')
                streak.current_streak = recalc['current_streak']
                streak.longest_streak = recalc['longest_streak']
                streak.last_active = recalc['last_active']
                streak.save()

                # --- Base karma with streak multiplier ---
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
                        created_at=now(),
                    )
                    from django.db.models import F
                    wallet, _ = Wallet.objects.get_or_create(user_id=user_id, defaults={'created_by_id': admin_id, 'updated_by_id': admin_id})
                    Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + karma_to_award)

                # --- Milestone karma (Expected vs Actual — idempotent) ---
                milestone_map = {
                    7:  (InternHashtag.STREAK_7_HASHTAG.value,  InternHashtag.STREAK_7_KARMA.value),
                    14: (InternHashtag.STREAK_14_HASHTAG.value, InternHashtag.STREAK_14_KARMA.value),
                    30: (InternHashtag.STREAK_30_HASHTAG.value, InternHashtag.STREAK_30_KARMA.value),
                    60: (InternHashtag.STREAK_60_HASHTAG.value, InternHashtag.STREAK_60_KARMA.value),
                    90: (InternHashtag.STREAK_90_HASHTAG.value, InternHashtag.STREAK_90_KARMA.value),
                }
                _award_missing_milestone_karma(user_id, admin_id, recalc['milestone_hits'], milestone_map)

                guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()
                if guild_link and guild_link.status == InternGuildStatus.AT_RISK.value:
                    guild_link.status = InternGuildStatus.ACTIVE.value
                    guild_link.save()

                # timesheet was already saved above; return early
                return CustomResponse(general_message="Timesheet approved successfully.").get_success_response()

            elif action == "reject":
                timesheet.status = InternSubmissionStatus.REJECTED.value
                timesheet.reviewed_by_id = admin_id
                timesheet.reviewed_at = now()
                timesheet.review_note = review_note

            timesheet.save()
            return CustomResponse(general_message="Timesheet rejected successfully.").get_success_response()

class InternWeeklyReviewReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
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

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
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
                # Save first so the recalculation includes this review
                review.save()

                user_id = review.user_id

                # --- Ground-up streak recalculation (order-independent) ---
                recalc = recalculate_intern_weekly_streak(user_id)

                streak, _ = UserStreak.objects.get_or_create(user_id=user_id, streak_type='intern_weekly_review')
                streak.current_streak = recalc['current_streak']
                streak.longest_streak = recalc['longest_streak']
                streak.last_active = recalc['last_active']
                streak.save()

                # --- Base karma for weekly review ---
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
                        created_at=now(),
                    )
                    from django.db.models import F
                    wallet, _ = Wallet.objects.get_or_create(user_id=user_id, defaults={'created_by_id': admin_id, 'updated_by_id': admin_id})
                    Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + karma_to_award)

                # weekly reviews currently have no milestone map, but the
                # pattern is here if needed in the future.

                # review was already saved above; skip the final save
                return CustomResponse(general_message=f"Weekly review {action}ed successfully.").get_success_response()

            elif action == "reject":
                review.status = InternSubmissionStatus.REJECTED.value
                review.reviewed_by_id = admin_id
                review.reviewed_at = now()
                review.review_note = review_note

            review.save()
            return CustomResponse(general_message=f"Weekly review {action}ed successfully.").get_success_response()


class InternWeeklyReviewListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
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

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
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
            ['user__full_name', 'status'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = ManageInternTimesheetSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()
