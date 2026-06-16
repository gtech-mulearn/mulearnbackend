from django.db import IntegrityError
from django.utils.timezone import now
from datetime import timedelta

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternSubmissionStatus, InternGuildStatus
from utils.utils import CommonUtils
from db.intern import InternWeeklyReview, UserInternGuildLink, InternTask, InternDailyTimesheet

from .serializers import InternWeeklyReviewSerializer, InternWeeklyReviewHistorySerializer


class InternWeeklyReviewPrefillAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Retrieve a snapshot of this week's tasks (COMPLETED / WAITING_FOR_REVIEW) "
            "to pre-populate the weekly review form before submission."
        ),
        responses={200: OpenApiResponse(description="Current week task snapshot.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        today = now().date()
        iso_year, iso_week, weekday = today.isocalendar()
        week_start = today - timedelta(days=weekday - 1)
        week_end = week_start + timedelta(days=6)

        tasks = InternTask.objects.filter(
            assigned_to_id=user_id,
            iso_week=iso_week,
            is_archived=False,
        ).order_by('deadline')

        task_list = [
            {
                "task_id": str(t.id),
                "title": t.title,
                "category": t.category,
                "complexity": t.complexity,
                "deadline": t.deadline.isoformat(),
                "status": t.status,
                "output_link": t.output_link,
            }
            for t in tasks
        ]

        return CustomResponse(response={
            "iso_year": iso_year,
            "iso_week": iso_week,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "tasks": task_list,
        }).get_success_response()


class InternWeeklyReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve weekly review(s). Pass a review_id to get a specific review.",
        responses={200: InternWeeklyReviewHistorySerializer},
    )
    def get(self, request, review_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if review_id:
            review = InternWeeklyReview.objects.filter(id=review_id, user_id=user_id).first()
            if not review:
                return CustomResponse(general_message="Weekly review not found.").get_failure_response()
            serializer = InternWeeklyReviewHistorySerializer(review)
            return CustomResponse(response=serializer.data).get_success_response()
            
        reviews = InternWeeklyReview.objects.filter(user_id=user_id).order_by('-iso_year', '-iso_week')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            reviews, request,
            ['iso_year', 'iso_week', 'status'],
            {'iso_year': 'iso_year', 'iso_week': 'iso_week', 'status': 'status'}
        )
        
        serializer = InternWeeklyReviewHistorySerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Submit a new weekly review.",
        request=InternWeeklyReviewSerializer,
        responses={200: OpenApiResponse(description="Weekly review submitted successfully.")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()
        
        if not guild_link or guild_link.status == InternGuildStatus.INACTIVE.value:
            return CustomResponse(general_message="Not an active intern.").get_failure_response()
            
        serializer = InternWeeklyReviewSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            try:
                serializer.save()
                return CustomResponse(general_message="Weekly review submitted successfully.").get_success_response()
            except IntegrityError:
                return CustomResponse(general_message="Review for this week already exists.", status_code=409).get_failure_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Edit a pending weekly review for the current week.",
        request=InternWeeklyReviewSerializer,
        responses={200: OpenApiResponse(description="Weekly review updated successfully.")},
    )
    def patch(self, request, review_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        review = InternWeeklyReview.objects.filter(id=review_id, user_id=user_id, status=InternSubmissionStatus.PENDING.value).first()
        if not review:
            return CustomResponse(general_message="Pending weekly review not found.").get_failure_response()
            
        today = now().date()
        iso_year, iso_week, _ = today.isocalendar()
        if review.iso_year != iso_year or review.iso_week != iso_week:
            return CustomResponse(general_message="Cannot edit reviews for past weeks.").get_failure_response()
            
        serializer = InternWeeklyReviewSerializer(review, data=request.data, partial=True, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Weekly review updated successfully.").get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

class InternWeeklyReviewCurrentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve the current week's submitted weekly review.",
        responses={200: InternWeeklyReviewHistorySerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        today = now().date()
        iso_year, iso_week, _ = today.isocalendar()
        
        review = InternWeeklyReview.objects.filter(user_id=user_id, iso_year=iso_year, iso_week=iso_week).first()
        if not review:
            return CustomResponse(general_message="No review submitted for the current week.").get_failure_response()
            
        serializer = InternWeeklyReviewHistorySerializer(review)
        return CustomResponse(response=serializer.data).get_success_response()

class InternWeeklyReviewHistoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve paginated intern weekly review history.",
        responses={200: InternWeeklyReviewHistorySerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        reviews = InternWeeklyReview.objects.filter(user_id=user_id).order_by('-iso_year', '-iso_week')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            reviews, request,
            ['iso_year', 'iso_week', 'status'],
            {'iso_year': 'iso_year', 'iso_week': 'iso_week', 'status': 'status'}
        )

        paged_reviews = paginated_queryset.get("queryset")

        # --- Batch fetch scoring data to avoid N+1 queries ---
        complexity_map = {'LOW': 1, 'MEDIUM': 2, 'HIGH': 3, 'CRITICAL': 5}

        # Group approved daily timesheets by (iso_year, iso_week)
        all_timesheets = InternDailyTimesheet.objects.filter(
            user_id=user_id, status='APPROVED'
        ).values_list('entry_date', flat=True)

        daily_count_by_week = {}
        for entry_date in all_timesheets:
            iso_year, iso_week, _ = entry_date.isocalendar()
            key = (iso_year, iso_week)
            daily_count_by_week[key] = daily_count_by_week.get(key, 0) + 1

        # Group verified task scores by (iso_year, iso_week) via deadline
        all_verified_tasks = InternTask.objects.filter(
            assigned_to_id=user_id, is_verified=True
        ).values('deadline', 'karma_awarded', 'complexity')

        task_score_by_week = {}
        for t in all_verified_tasks:
            iso_year, iso_week, _ = t['deadline'].isocalendar()
            key = (iso_year, iso_week)
            task_score_by_week[key] = task_score_by_week.get(key, 0) + (
                t['karma_awarded'] * complexity_map.get(t['complexity'], 1)
            )

        # Serialize and annotate each review with its weekly score
        serializer = InternWeeklyReviewHistorySerializer(paged_reviews, many=True)
        data = serializer.data

        for i, review in enumerate(paged_reviews):
            week_key = (review.iso_year, review.iso_week)
            weekly_score = (
                daily_count_by_week.get(week_key, 0) * 25 +
                (50 if review.status == 'APPROVED' else 0) +
                task_score_by_week.get(week_key, 0)
            )
            data[i]['score'] = weekly_score

        return CustomResponse(
            response={
                "data": data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()


