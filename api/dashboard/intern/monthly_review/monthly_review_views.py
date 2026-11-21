import calendar

from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework.views import APIView

from db.intern import InternMonthlyReview, UserInternGuildLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternSubmissionStatus, InternGuildStatus
from utils.utils import CommonUtils, DateTimeUtils

from .serializers import (
    InternMonthlyReviewSerializer,
    InternMonthlyReviewHistorySerializer,
    month_tasks,
    task_snapshot,
)
from .leave import approved_leave_days, leave_days_by_review
from .window import get_monthly_review_window, window_for_month

LIST_SEARCH_FIELDS = ['status', 'team']
LIST_SORT_FIELDS = {'year': 'year', 'month': 'month', 'status': 'status', 'created_at': 'created_at'}


def _current_window(today=None):
    return get_monthly_review_window(today or DateTimeUtils.get_ist_today())


def _month_label(window):
    return f"{calendar.month_name[window.month]} {window.year}"


def _window_closed_response(window):
    return CustomResponse(
        general_message=(
            f"The monthly review window is closed. The {_month_label(window)} review opens on "
            f"{window.opens_on:%d %b %Y} and closes on {window.closes_on:%d %b %Y}."
        ),
        response={"window": window.to_dict()},
    ).get_failure_response()


def _duplicate_review_response(window):
    return CustomResponse(
        general_message=f"A review for {_month_label(window)} has already been submitted."
    ).get_failure_response(status_code=409, http_status_code=409)


def _paginated_reviews(request, user_id):
    reviews = InternMonthlyReview.objects.filter(user_id=user_id).order_by('-year', '-month')
    paginated_queryset = CommonUtils.get_paginated_queryset(
        reviews, request, LIST_SEARCH_FIELDS, LIST_SORT_FIELDS
    )
    page = list(paginated_queryset.get("queryset"))
    serializer = InternMonthlyReviewHistorySerializer(
        page, many=True, context={'leave_days': leave_days_by_review(page)}
    )
    return CustomResponse(
        response={
            "data": serializer.data,
            "pagination": paginated_queryset.get("pagination"),
        }
    ).get_success_response()


class InternMonthlyReviewPrefillAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Monthly review form data: whether the submission window is open (IST), "
            "which month it is for, that month's tasks, and the intern's existing "
            "review for that month, if any. When the window is closed, the next "
            "window is returned with window_open=false. `leave_days` is the intern's "
            "approved leave days (WFH included) in that month up to today; it is shown "
            "on the form only and is not sent back on submit."
        ),
        responses={200: OpenApiResponse(description="Window state, month task snapshot and leave days so far.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        today = DateTimeUtils.get_ist_today()
        window = _current_window(today)

        existing = (
            InternMonthlyReview.objects
            .filter(user_id=user_id, year=window.year, month=window.month)
            .values('id', 'status', 'review_note')
            .first()
        )

        return CustomResponse(response={
            **window.to_dict(),
            "existing_review": existing,
            "leave_days": approved_leave_days(
                user_id, window.period_start, min(today, window.period_end)
            ),
            "tasks": [task_snapshot(t, status_key='status') for t in month_tasks(user_id, window)],
        }).get_success_response()


class InternMonthlyReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="List the intern's monthly reviews (paginated), or one review when review_id is given.",
        responses={200: InternMonthlyReviewHistorySerializer},
    )
    def get(self, request, review_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if review_id:
            review = InternMonthlyReview.objects.filter(id=review_id, user_id=user_id).first()
            if not review:
                return CustomResponse(general_message="Monthly review not found.").get_failure_response()
            return CustomResponse(
                response=InternMonthlyReviewHistorySerializer(review).data
            ).get_success_response()
        return _paginated_reviews(request, user_id)

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Submit the monthly review. Only accepted while the window is open (last 2 days "
            "of the month + first 2 days of the next, IST); the server decides which month "
            "it is for. If this month's review was rejected, submitting again replaces it "
            "and sends it back for review. Returns 409 if a pending or approved review exists. "
            "leave_days is not accepted; responses show approved leave days for the month."
        ),
        request=InternMonthlyReviewSerializer,
        responses={
            200: InternMonthlyReviewHistorySerializer,
            409: OpenApiResponse(description="A review for this month already exists."),
        },
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()
        if not guild_link or guild_link.status == InternGuildStatus.INACTIVE.value:
            return CustomResponse(general_message="Not an active intern.").get_failure_response()

        window = _current_window()
        if not window.is_open:
            return _window_closed_response(window)

        context = {'user_id': user_id, 'window': window, 'team': guild_link.guild}

        try:
            with transaction.atomic():
                existing = (
                    InternMonthlyReview.objects.select_for_update()
                    .filter(user_id=user_id, year=window.year, month=window.month)
                    .first()
                )
                if existing and existing.status != InternSubmissionStatus.REJECTED.value:
                    return _duplicate_review_response(window)

                if existing:
                    serializer = InternMonthlyReviewSerializer(
                        existing, data=request.data, context={**context, 'resubmit': True}
                    )
                    message = "Monthly review resubmitted successfully."
                else:
                    serializer = InternMonthlyReviewSerializer(data=request.data, context=context)
                    message = "Monthly review submitted successfully."

                if not serializer.is_valid():
                    return CustomResponse(response=serializer.errors).get_failure_response()
                review = serializer.save()
        except IntegrityError:
            # Two submissions raced past the existence check; the unique key
            # (user_id, year, month) let only one through.
            return _duplicate_review_response(window)

        return CustomResponse(
            general_message=message,
            response=InternMonthlyReviewHistorySerializer(review).data,
        ).get_success_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Edit a pending monthly review while its submission window is still open.",
        request=InternMonthlyReviewSerializer,
        responses={200: InternMonthlyReviewHistorySerializer},
    )
    def patch(self, request, review_id):
        user_id = JWTUtils.fetch_user_id(request)

        window = _current_window()
        with transaction.atomic():
            review = (
                InternMonthlyReview.objects.select_for_update()
                .filter(id=review_id, user_id=user_id, status=InternSubmissionStatus.PENDING.value)
                .first()
            )
            if not review:
                return CustomResponse(general_message="Pending monthly review not found.").get_failure_response()

            if not window.is_open or (review.year, review.month) != (window.year, window.month):
                return CustomResponse(
                    general_message="This review can no longer be edited; its submission window has closed."
                ).get_failure_response()

            serializer = InternMonthlyReviewSerializer(
                review, data=request.data, partial=True,
                context={'user_id': user_id, 'window': window},
            )
            if not serializer.is_valid():
                return CustomResponse(response=serializer.errors).get_failure_response()
            review = serializer.save()

        return CustomResponse(
            general_message="Monthly review updated successfully.",
            response=InternMonthlyReviewHistorySerializer(review).data,
        ).get_success_response()


class InternMonthlyReviewCurrentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "The review for the open window's month, or, when no window is open, for the "
            "most recent month whose window has closed. `review` is null if none was submitted."
        ),
        responses={200: OpenApiResponse(description="Window and the matching review (or null).")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        window = _current_window()
        if not window.is_open:
            # The next window is for the current month; show the last one instead.
            prev_year, prev_month = (
                (window.year, window.month - 1) if window.month > 1 else (window.year - 1, 12)
            )
            window = window_for_month(prev_year, prev_month)

        review = InternMonthlyReview.objects.filter(
            user_id=user_id, year=window.year, month=window.month
        ).first()

        return CustomResponse(response={
            "window": window.to_dict(),
            "review": InternMonthlyReviewHistorySerializer(review).data if review else None,
        }).get_success_response()


class InternMonthlyReviewHistoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Paginated monthly review history, newest month first.",
        responses={200: InternMonthlyReviewHistorySerializer(many=True)},
    )
    def get(self, request):
        return _paginated_reviews(request, JWTUtils.fetch_user_id(request))
