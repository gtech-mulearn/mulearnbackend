from datetime import date
import uuid

from django.db import transaction
from django.utils.timezone import now
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternSubmissionStatus, InternHashtag
from db.intern import InternDailyTimesheet, InternWeeklyReview, InternMonthlyReview
from db.task import KarmaActivityLog, TaskList, Wallet
from db.achievement import UserStreak
from utils.utils import CommonUtils
from utils.karma import notify_karma_change
from api.notification.types import NotificationType
from api.dashboard.intern.monthly_review.leave import leave_days_by_review
from .serializers import (
    ManageInternWeeklyReviewSerializer,
    ManageInternTimesheetSerializer,
    ManageInternMonthlyReviewSerializer,
)

REVIEW_NOTE_MAX_LENGTH = 300
# Monthly review admin endpoints leave out the plain Intern role that the
# older manage-interns endpoints allow, so an intern cannot approve their own
# monthly review.
MONTHLY_REVIEW_ADMIN_ROLES = [RoleType.ADMIN.value, RoleType.INTERN_LEAD.value]


# ============================================================================
# Streak Recalculation Helpers
# ============================================================================

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


class InternTimesheetReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    # Read-only: daily timesheets are no longer approved or rejected by admins —
    # they count as soon as the intern submits them. The former PATCH
    # (approve/reject) has been removed; its streak/karma logic now runs on
    # submit (api/dashboard/intern/timesheet/streak.py).
    # Plain interns are excluded: this returns any intern's timesheet by id.
    # Interns read their own through intern/timesheets/.
    @role_required([RoleType.ADMIN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve a single intern timesheet (read-only).",
        responses={200: ManageInternTimesheetSerializer},
    )
    def get(self, request, timesheet_id):
        timesheet = InternDailyTimesheet.objects.select_related('user').filter(id=timesheet_id).first()
        if not timesheet:
            return CustomResponse(general_message="Timesheet not found.").get_failure_response()
        serializer = ManageInternTimesheetSerializer(timesheet)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Deprecated: daily timesheets no longer require approval. Always returns a failure.",
        responses={400: OpenApiResponse(description="Timesheet approval has been removed.")},
    )
    def patch(self, request, timesheet_id):
        # Kept so clients still calling approve/reject get the standard
        # envelope with a clear message instead of a bare 405.
        return CustomResponse(
            general_message="Daily timesheets no longer require approval; they count as soon as they are submitted."
        ).get_failure_response()


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
                    kal = KarmaActivityLog.objects.create(
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
                    notify_karma_change(
                        NotificationType.KARMA_AWARDED, user_id, admin_id, task_list.title, karma_to_award, kal.id
                    )

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

    # Plain interns are excluded: this lists every intern's timesheets.
    # Interns read their own through intern/timesheets/.
    @role_required([RoleType.ADMIN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "List intern timesheets (read-only). Optional filters: "
            "`muid` (exact), `date_from` / `date_to` (YYYY-MM-DD, on entry_date, inclusive), "
            "`status` (legacy rows may be APPROVED/REJECTED/PENDING; new ones are SUBMITTED)."
        ),
        parameters=[
            OpenApiParameter(name='muid', description='Intern muid', required=False, type=str),
            OpenApiParameter(name='date_from', description='entry_date >= (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='date_to', description='entry_date <= (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='status', description='Timesheet status', required=False, type=str),
        ],
        responses={200: ManageInternTimesheetSerializer(many=True)},
    )
    def get(self, request):
        timesheets = InternDailyTimesheet.objects.select_related('user').order_by('-created_at')

        muid = request.query_params.get('muid')
        if muid:
            timesheets = timesheets.filter(user__muid=muid)

        for param, lookup in (('date_from', 'entry_date__gte'), ('date_to', 'entry_date__lte')):
            value = request.query_params.get(param)
            if not value:
                continue
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                return CustomResponse(
                    general_message=f"Invalid {param}. Use YYYY-MM-DD."
                ).get_failure_response()
            timesheets = timesheets.filter(**{lookup: parsed})

        status = request.query_params.get('status')
        if status:
            timesheets = timesheets.filter(status=status)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            timesheets, request,
            ['user__full_name', 'user__muid', 'status'],
            {'created_at': 'created_at', 'entry_date': 'entry_date', 'status': 'status'}
        )
        
        serializer = ManageInternTimesheetSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()


# ============================================================================
# Monthly reviews
# ============================================================================

def log_monthly_review_activity(user_id: str, actor_id: str):
    """
    Writes the #intern-monthly-review activity row so an approved review shows
    in the intern's Quest Log. Skipped when the task_list row is missing.
    Karma is InternHashtag.MONTHLY_REVIEW_KARMA (currently 0); the wallet and
    a karma notification are only touched when it is > 0. No streak.
    """
    task_list = TaskList.objects.filter(hashtag=InternHashtag.MONTHLY_REVIEW_HASHTAG.value).first()
    if not task_list:
        return

    karma = InternHashtag.MONTHLY_REVIEW_KARMA.value
    kal = KarmaActivityLog.objects.create(
        id=str(uuid.uuid4()),
        user_id=user_id,
        task=task_list,
        karma=karma,
        appraiser_approved=True,
        updated_by_id=actor_id,
        updated_at=now(),
        created_by_id=actor_id,
        created_at=now(),
    )

    if karma > 0:
        from django.db.models import F
        wallet, _ = Wallet.objects.get_or_create(
            user_id=user_id, defaults={'created_by_id': actor_id, 'updated_by_id': actor_id}
        )
        Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + karma)
        notify_karma_change(
            NotificationType.KARMA_AWARDED, user_id, actor_id, task_list.title, karma, kal.id
        )


class InternMonthlyReviewListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "List intern monthly reviews, newest month first. Optional filters: "
            "`status` (PENDING/APPROVED/REJECTED), `year`, `month` (1-12), `muid` (exact). "
            "`search` matches name, muid and team. `leave_days` is the intern's approved "
            "leave days (WFH included) in the review month, worked out from leave requests."
        ),
        parameters=[
            OpenApiParameter(name='status', description='Review status', required=False, type=str),
            OpenApiParameter(name='year', description='Reviewed year, e.g. 2026', required=False, type=int),
            OpenApiParameter(name='month', description='Reviewed month, 1-12', required=False, type=int),
            OpenApiParameter(name='muid', description='Intern muid', required=False, type=str),
        ],
        responses={200: ManageInternMonthlyReviewSerializer(many=True)},
    )
    def get(self, request):
        reviews = InternMonthlyReview.objects.select_related('user').order_by('-year', '-month', '-created_at')

        status = request.query_params.get('status')
        if status:
            reviews = reviews.filter(status=status)

        muid = request.query_params.get('muid')
        if muid:
            reviews = reviews.filter(user__muid=muid)

        for param, low, high in (('year', 2000, 2100), ('month', 1, 12)):
            value = request.query_params.get(param)
            if not value:
                continue
            try:
                parsed = int(value)
            except ValueError:
                parsed = None
            if parsed is None or not low <= parsed <= high:
                return CustomResponse(
                    general_message=f"Invalid {param}. Use a number from {low} to {high}."
                ).get_failure_response()
            reviews = reviews.filter(**{param: parsed})

        paginated_queryset = CommonUtils.get_paginated_queryset(
            reviews, request,
            ['user__full_name', 'user__muid', 'team'],
            {'created_at': 'created_at', 'year': 'year', 'month': 'month', 'status': 'status'}
        )

        # One leave query for the whole page instead of one per review.
        page = list(paginated_queryset.get("queryset"))
        serializer = ManageInternMonthlyReviewSerializer(
            page, many=True, context={'leave_days': leave_days_by_review(page)}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()


class InternMonthlyReviewReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve one intern monthly review.",
        responses={200: ManageInternMonthlyReviewSerializer},
    )
    def get(self, request, review_id):
        review = InternMonthlyReview.objects.select_related('user').filter(id=review_id).first()
        if not review:
            return CustomResponse(general_message="Monthly review not found.").get_failure_response()
        return CustomResponse(
            response=ManageInternMonthlyReviewSerializer(review).data
        ).get_success_response()

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Approve or reject a pending monthly review. Body: "
            "`{\"action\": \"approve\" | \"reject\", \"review_note\": \"...\"}` "
            "(review_note optional, max 300 characters). A rejected review can be "
            "resubmitted by the intern while its window is still open."
        ),
        responses={200: ManageInternMonthlyReviewSerializer},
    )
    def patch(self, request, review_id):
        admin_id = JWTUtils.fetch_user_id(request)
        action = request.data.get("action")
        review_note = request.data.get("review_note")

        if action not in ("approve", "reject"):
            return CustomResponse(general_message="Invalid action. Must be 'approve' or 'reject'.").get_failure_response()
        if review_note is not None and not isinstance(review_note, str):
            return CustomResponse(general_message="review_note must be text.").get_failure_response()
        review_note = (review_note or "").strip() or None
        if review_note and len(review_note) > REVIEW_NOTE_MAX_LENGTH:
            return CustomResponse(
                general_message=f"review_note cannot exceed {REVIEW_NOTE_MAX_LENGTH} characters."
            ).get_failure_response()

        with transaction.atomic():
            review = (
                # No select_related here: FOR UPDATE would also lock the joined user row.
                InternMonthlyReview.objects.select_for_update()
                .filter(id=review_id, status=InternSubmissionStatus.PENDING.value)
                .first()
            )
            if not review:
                return CustomResponse(general_message="Pending monthly review not found.").get_failure_response()

            review.status = (
                InternSubmissionStatus.APPROVED.value if action == "approve"
                else InternSubmissionStatus.REJECTED.value
            )
            review.reviewed_by_id = admin_id
            review.reviewed_at = now()
            review.review_note = review_note
            review.updated_by_id = admin_id
            review.save(update_fields=['status', 'reviewed_by', 'reviewed_at', 'review_note', 'updated_by', 'updated_at'])

            if action == "approve":
                log_monthly_review_activity(review.user_id, admin_id)

        return CustomResponse(
            general_message=f"Monthly review {action}d successfully.",
            response=ManageInternMonthlyReviewSerializer(review).data,
        ).get_success_response()
