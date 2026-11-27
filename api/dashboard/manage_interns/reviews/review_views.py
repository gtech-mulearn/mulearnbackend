from datetime import date, timedelta
import uuid

from django.db import transaction
from django.utils.timezone import now
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from utils.intern_permissions import (
    by_current_members, caller_team_id, include_former, is_admin, scope_records, self_review_error,
)
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternSubmissionStatus, InternHashtag
from db.intern import InternDailyTimesheet, InternWeeklyReview, InternMonthlyReview, UserInternTeamLink
from db.task import KarmaActivityLog, TaskList, Wallet
from db.achievement import UserStreak
from utils.utils import CommonUtils
from utils.karma import notify_karma_change
from api.notification.types import NotificationType
from api.dashboard.intern.monthly_review.leave import leave_days_by_review
from api.dashboard.intern.monthly_review.window import window_for_month
from .missing import daily_missing, monthly_missing, person
from utils.utils import DateTimeUtils
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
        description=(
            "Retrieve a single intern timesheet (read-only). Admin: any timesheet. Intern Lead: "
            "timesheets submitted in their team, including those of people who have since left."
        ),
        responses={200: ManageInternTimesheetSerializer},
    )
    def get(self, request, timesheet_id):
        timesheet = (
            scope_records(InternDailyTimesheet.objects.select_related('user', 'team', 'reviewed_by'), request)
            .filter(id=timesheet_id).first()
        )
        if not timesheet:
            return CustomResponse(general_message="Timesheet not found.").get_failure_response()
        serializer = ManageInternTimesheetSerializer(timesheet)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Add or change the review note on a timesheet: `{\"review_note\": \"...\"}` (max 300 "
            "characters). There is no approval: the timesheet still counts as submitted, only the "
            "note, reviewed_by and reviewed_at are set. The intern sees the note on their timesheet. "
            "Admin: any timesheet. Intern Lead: timesheets submitted in their team (former members "
            "included), not their own."
        ),
        responses={200: ManageInternTimesheetSerializer},
    )
    def patch(self, request, timesheet_id):
        if 'action' in request.data:
            # Old approve/reject clients.
            return CustomResponse(
                general_message=(
                    "Daily timesheets no longer require approval; they count as soon as they are "
                    "submitted. Send review_note to comment on one."
                )
            ).get_failure_response()

        review_note = request.data.get("review_note")
        if not isinstance(review_note, str) or not review_note.strip():
            return CustomResponse(general_message="review_note is required.").get_failure_response()
        review_note = review_note.strip()
        if len(review_note) > REVIEW_NOTE_MAX_LENGTH:
            return CustomResponse(
                general_message=f"review_note cannot exceed {REVIEW_NOTE_MAX_LENGTH} characters."
            ).get_failure_response()

        actor_id = JWTUtils.fetch_user_id(request)
        with transaction.atomic():
            timesheet = (
                scope_records(InternDailyTimesheet.objects.select_for_update(), request)
                .filter(id=timesheet_id).first()
            )
            if not timesheet:
                return CustomResponse(general_message="Timesheet not found.").get_failure_response()
            own = self_review_error(request, timesheet.user_id, "timesheet")
            if own:
                return CustomResponse(general_message=own).get_failure_response()

            timesheet.review_note = review_note
            timesheet.reviewed_by_id = actor_id
            timesheet.reviewed_at = now()
            timesheet.save(update_fields=['review_note', 'reviewed_by', 'reviewed_at', 'updated_at'])

        timesheet = InternDailyTimesheet.objects.select_related('user', 'team', 'reviewed_by').get(id=timesheet.id)
        return CustomResponse(
            general_message="Review note saved.",
            response=ManageInternTimesheetSerializer(timesheet).data,
        ).get_success_response()


def _scoped_weekly_reviews(request):
    """
    Weekly reviews the caller may manage: all for an Admin; for a Lead, those of
    current members of their team (weekly reviews have no team_id).
    """
    reviews = InternWeeklyReview.objects.all()
    if is_admin(request):
        return reviews
    team_id = caller_team_id(request)
    if not team_id:
        return reviews.none()
    return reviews.filter(
        user_id__in=UserInternTeamLink.objects.filter(team_id=team_id, is_current=True).values('user_id')
    )


class InternWeeklyReviewReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve a weekly review for detail.",
        responses={200: ManageInternWeeklyReviewSerializer},
    )
    def get(self, request, review_id):
        review = _scoped_weekly_reviews(request).filter(id=review_id).first()
        if not review:
            return CustomResponse(general_message="Weekly review not found.").get_failure_response()
        serializer = ManageInternWeeklyReviewSerializer(review)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
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
            
        review = _scoped_weekly_reviews(request).filter(id=review_id, status=InternSubmissionStatus.PENDING.value).first()
        if not review:
            return CustomResponse(general_message="Pending weekly review not found.").get_failure_response()
        own = self_review_error(request, review.user_id, "weekly review")
        if own:
            return CustomResponse(general_message=own).get_failure_response()
            
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

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="List weekly reviews with filters.",
        responses={200: ManageInternWeeklyReviewSerializer(many=True)},
    )
    def get(self, request):
        reviews = _scoped_weekly_reviews(request).order_by('-created_at')
        
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
            "List intern timesheets (read-only). Admin: every team (optional `team_id`). Intern "
            "Lead: timesheets submitted in their team. By default only timesheets of people who "
            "are still current members of the team they were submitted in (members marked "
            "INACTIVE included); `include_former=true` also returns those of people who have left "
            "(moved or deactivated), and, for Admins, timesheets from before teams. Optional "
            "filters: `muid` (exact), `date_from` / `date_to` (YYYY-MM-DD, on entry_date, inclusive)."
        ),
        parameters=[
            OpenApiParameter(name='team_id', description='Admin only: one team', required=False, type=str),
            OpenApiParameter(name='include_former', description='true: also people who left the team', required=False, type=str),
            OpenApiParameter(name='muid', description='Intern muid', required=False, type=str),
            OpenApiParameter(name='date_from', description='entry_date >= (YYYY-MM-DD)', required=False, type=str),
            OpenApiParameter(name='date_to', description='entry_date <= (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={200: ManageInternTimesheetSerializer(many=True)},
    )
    def get(self, request):
        timesheets = scope_records(
            InternDailyTimesheet.objects.select_related('user', 'team', 'reviewed_by'), request
        ).order_by('-created_at')
        if not include_former(request):
            timesheets = by_current_members(timesheets)

        team_id = request.query_params.get('team_id')
        if team_id and is_admin(request):
            timesheets = timesheets.filter(team_id=team_id)

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

        paginated_queryset = CommonUtils.get_paginated_queryset(
            timesheets, request,
            ['user__full_name', 'user__muid'],
            {'created_at': 'created_at', 'entry_date': 'entry_date'}
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
            "List intern monthly reviews, newest month first. Admin: every team (optional "
            "`team_id`). Intern Lead: reviews submitted in their team. By default only reviews of "
            "people who are still current members of that team (members marked INACTIVE "
            "included); `include_former=true` also returns those of people who have left, and, for "
            "Admins, reviews from before teams. Optional filters: `status` "
            "(PENDING/APPROVED/REJECTED), `year`, `month` (1-12), `muid` (exact). `search` matches "
            "name, muid and team name. `leave_days` is the intern's approved leave days (WFH "
            "included) in the review month, worked out from leave requests."
        ),
        parameters=[
            OpenApiParameter(name='team_id', description='Admin only: one team', required=False, type=str),
            OpenApiParameter(name='include_former', description='true: also people who left the team', required=False, type=str),
            OpenApiParameter(name='status', description='Review status', required=False, type=str),
            OpenApiParameter(name='year', description='Reviewed year, e.g. 2026', required=False, type=int),
            OpenApiParameter(name='month', description='Reviewed month, 1-12', required=False, type=int),
            OpenApiParameter(name='muid', description='Intern muid', required=False, type=str),
        ],
        responses={200: ManageInternMonthlyReviewSerializer(many=True)},
    )
    def get(self, request):
        reviews = scope_records(
            InternMonthlyReview.objects.select_related('user', 'team', 'reviewed_by'), request
        ).order_by('-year', '-month', '-created_at')
        if not include_former(request):
            reviews = by_current_members(reviews)

        team_id = request.query_params.get('team_id')
        if team_id and is_admin(request):
            reviews = reviews.filter(team_id=team_id)

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
            ['user__full_name', 'user__muid', 'team__name'],
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
        description=(
            "Retrieve one intern monthly review. Admin: any review. Intern Lead: reviews "
            "submitted in their team, including those of people who have since left."
        ),
        responses={200: ManageInternMonthlyReviewSerializer},
    )
    def get(self, request, review_id):
        review = (
            scope_records(InternMonthlyReview.objects.select_related('user', 'team', 'reviewed_by'), request)
            .filter(id=review_id).first()
        )
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
            "resubmitted by the intern while its window is still open. Admin: any review. "
            "Intern Lead: reviews submitted in their team, not their own."
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
                scope_records(InternMonthlyReview.objects.select_for_update(), request)
                .filter(id=review_id, status=InternSubmissionStatus.PENDING.value)
                .first()
            )
            if review:
                own = self_review_error(request, review.user_id, "monthly review")
                if own:
                    return CustomResponse(general_message=own).get_failure_response()
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


DAILY_EXPORT_MAX_DAYS = 92
MONTHLY_EXPORT_MAX_MONTHS = 24


def _bad(message):
    return CustomResponse(general_message=message).get_failure_response()


def _parse_month(value, default):
    """'YYYY-MM' -> (year, month), the default when empty, None when invalid."""
    if not value:
        return default
    try:
        year, month = (int(x) for x in str(value).split('-')[:2])
    except ValueError:
        return None
    return (year, month) if 2000 <= year <= 2100 and 1 <= month <= 12 else None


def _months(first, last):
    """MonthlyReviewWindow for every month from first to last, (year, month) tuples."""
    out, (y, m) = [], first
    while (y, m) <= last:
        out.append(window_for_month(y, m))
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    return out


def _last_month(today):
    return (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)


def _csv(name, header, rows):
    """A CSV download through CommonUtils.generate_csv; `name` has no extension."""
    return CommonUtils.generate_csv([dict(zip(header, row)) for row in rows], name)


# ?search matches name or muid in the built rows (CommonUtils pages lists too).
MISSING_SEARCH_FIELDS = ['full_name', 'muid']
MISSING_PARAMS = [
    OpenApiParameter(name='team_id', description='Admin only: one team', required=False, type=str),
]
MISSING_RULES = (
    "Each membership row counts for its tenure (join_date..end_date), current or ended, so "
    "former members are checked for the time they were in the team and gaps between stints "
    "aren't. Checked per person. Leave doesn't hide anyone; it is shown on each entry. Admin: "
    "every team (optional `team_id`). Intern Lead: their own team."
)


class InternMonthlyReviewMissingAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Who hasn't submitted the monthly review for one month (paginated with pageIndex / "
            "perPage, `search` on name and muid). `year` and `month` pick the month (default: last "
            "month; future months are refused). Submitted means a PENDING or APPROVED review for "
            "that month, in any team; REJECTED counts as missing. Someone whose tenure ends before "
            "the month's window closes is left out: they leave during the window and can't "
            "submit once their tenure has ended. `leave_days` = approved leave days in the "
            "month. `window_open` says whether people can still submit. " + MISSING_RULES
        ),
        parameters=MISSING_PARAMS + [
            OpenApiParameter(name='year', description='Year, e.g. 2026', required=False, type=int),
            OpenApiParameter(name='month', description='Month, 1-12', required=False, type=int),
        ],
        responses={200: OpenApiResponse(description="year, month, window_open, data, pagination")},
    )
    def get(self, request):
        today = DateTimeUtils.get_ist_today()
        last_year, last_month = _last_month(today)
        try:
            year = int(request.query_params.get('year') or last_year)
            month = int(request.query_params.get('month') or last_month)
        except ValueError:
            return _bad("year and month must be numbers.")
        if not (2000 <= year <= 2100 and 1 <= month <= 12):
            return _bad("Use a year from 2000 to 2100 and a month from 1 to 12.")
        if (year, month) > (today.year, today.month):
            return _bad("That month hasn't started yet.")

        window = window_for_month(year, month)
        items = sorted(monthly_missing(request, [window]), key=lambda x: (x[1].user.full_name or '').lower())
        page = CommonUtils.get_paginated_queryset(
            [{**person(row), "leave_days": days} for _, row, days in items], request, MISSING_SEARCH_FIELDS,
        )
        return CustomResponse(response={
            "year": year,
            "month": month,
            "window_open": window.opens_on <= today <= window.closes_on,
        }).paginated_response(data=list(page["queryset"]), pagination=page["pagination"])


class InternMonthlyReviewMissingExportAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(MONTHLY_REVIEW_ADMIN_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "CSV: who didn't submit the monthly review, one row per person per month, for "
            "`from`..`to` (YYYY-MM, inclusive; default last month; at most 24 months; no future "
            "months). Same rules as monthly/missing/. " + MISSING_RULES
        ),
        parameters=MISSING_PARAMS + [
            OpenApiParameter(name='from', description='First month, YYYY-MM', required=False, type=str),
            OpenApiParameter(name='to', description='Last month, YYYY-MM', required=False, type=str),
        ],
        responses={200: OpenApiResponse(description="CSV attachment.")},
    )
    def get(self, request):
        today = DateTimeUtils.get_ist_today()
        default = _last_month(today)
        first = _parse_month(request.query_params.get('from'), default)
        last = _parse_month(request.query_params.get('to'), first or default)
        if first is None or last is None:
            return _bad("from and to must be months (YYYY-MM).")
        if first > last:
            return _bad("from can't be after to.")
        if last > (today.year, today.month):
            return _bad("to can't be a month that hasn't started yet.")
        months = _months(first, last)
        if len(months) > MONTHLY_EXPORT_MAX_MONTHS:
            return _bad(f"At most {MONTHLY_EXPORT_MAX_MONTHS} months per export.")

        items = sorted(
            monthly_missing(request, months),
            key=lambda x: (x[0].year, x[0].month, x[1].team.name, (x[1].user.full_name or '').lower()),
        )
        return _csv(
            f"missing_monthly_reviews_{first[0]}-{first[1]:02d}_to_{last[0]}-{last[1]:02d}",
            ['Month', 'Full Name', 'MuID', 'Team', 'Team Code', 'Status', 'Leave Days'],
            [
                [f"{w.year}-{w.month:02d}", row.user.full_name, row.user.muid, row.team.name,
                 row.team.code, row.intern_status, days]
                for w, row, days in items
            ],
        )


class InternTimesheetMissingAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Who hasn't submitted a timesheet for one day (paginated with pageIndex / perPage, "
            "`search` on name and muid). `date` (YYYY-MM-DD, IST) defaults to today; future dates "
            "are refused. Weekends are included (`is_weekend`). `on_leave` / `leave_type` say "
            "whether approved leave covers the day; `on_leave=false` lists only people who weren't "
            "on leave. `can_still_submit` is true for today and yesterday. " + MISSING_RULES
        ),
        parameters=MISSING_PARAMS + [
            OpenApiParameter(name='date', description='YYYY-MM-DD, default today', required=False, type=str),
            OpenApiParameter(name='on_leave', description='true / false', required=False, type=str),
        ],
        responses={200: OpenApiResponse(description="date, is_weekend, can_still_submit, data, pagination")},
    )
    def get(self, request):
        today = DateTimeUtils.get_ist_today()
        value = request.query_params.get('date')
        try:
            day = date.fromisoformat(value) if value else today
        except ValueError:
            return _bad("Invalid date. Use YYYY-MM-DD.")
        if day > today:
            return _bad("That day hasn't come yet.")

        items = sorted(daily_missing(request, day, day), key=lambda x: (x[1].user.full_name or '').lower())
        on_leave = (request.query_params.get('on_leave') or '').lower()
        if on_leave in ('true', 'false'):
            items = [x for x in items if (x[2] is not None) == (on_leave == 'true')]
        page = CommonUtils.get_paginated_queryset(
            [{**person(row), "on_leave": kind is not None, "leave_type": kind} for _, row, kind in items],
            request, MISSING_SEARCH_FIELDS,
        )
        return CustomResponse(response={
            "date": day.isoformat(),
            "is_weekend": day.weekday() > 4,
            "can_still_submit": day >= today - timedelta(days=1),
        }).paginated_response(data=list(page["queryset"]), pagination=page["pagination"])


class InternTimesheetMissingExportAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "CSV: who didn't submit a timesheet, one row per person per day, for `from`..`to` "
            "(YYYY-MM-DD, inclusive; default today; at most 92 days; no future dates). Same rules "
            "as timesheets/missing/. " + MISSING_RULES
        ),
        parameters=MISSING_PARAMS + [
            OpenApiParameter(name='from', description='First day, YYYY-MM-DD', required=False, type=str),
            OpenApiParameter(name='to', description='Last day, YYYY-MM-DD', required=False, type=str),
        ],
        responses={200: OpenApiResponse(description="CSV attachment.")},
    )
    def get(self, request):
        today = DateTimeUtils.get_ist_today()
        try:
            first = date.fromisoformat(request.query_params['from']) if request.query_params.get('from') else today
            last = date.fromisoformat(request.query_params['to']) if request.query_params.get('to') else first
        except ValueError:
            return _bad("from and to must be dates (YYYY-MM-DD).")
        if first > last:
            return _bad("from can't be after to.")
        if last > today:
            return _bad("to can't be in the future.")
        if (last - first).days + 1 > DAILY_EXPORT_MAX_DAYS:
            return _bad(f"At most {DAILY_EXPORT_MAX_DAYS} days per export.")

        items = sorted(
            daily_missing(request, first, last),
            key=lambda x: (x[0], x[1].team.name, (x[1].user.full_name or '').lower()),
        )
        return _csv(
            f"missing_timesheets_{first.isoformat()}_to_{last.isoformat()}",
            ['Date', 'Day', 'Weekend', 'Full Name', 'MuID', 'Team', 'Team Code', 'Status', 'On Leave', 'Leave Type'],
            [
                [d.isoformat(), d.strftime('%a'), 'Yes' if d.weekday() > 4 else 'No', row.user.full_name,
                 row.user.muid, row.team.name, row.team.code, row.intern_status,
                 'Yes' if kind else 'No', kind or '']
                for d, row, kind in items
            ],
        )
