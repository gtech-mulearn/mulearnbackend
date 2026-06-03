from django.db import IntegrityError
from django.utils.timezone import now

from rest_framework.views import APIView

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternSubmissionStatus, InternGuildStatus
from utils.utils import CommonUtils
from db.intern import InternWeeklyReview, UserInternGuildLink

from .serializers import InternWeeklyReviewSerializer, InternWeeklyReviewHistorySerializer

class InternWeeklyReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
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
    def patch(self, request, review_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        review = InternWeeklyReview.objects.filter(id=review_id, user_id=user_id, status=InternSubmissionStatus.PENDING.value).first()
        if not review:
            return CustomResponse(general_message="Pending weekly review not found.").get_failure_response()
            
        today = now().date()
        iso_year, iso_week, _ = today.isocalendar()
        if review.iso_year != iso_year or review.iso_week != iso_week:
            return CustomResponse(general_message="Cannot edit reviews for past weeks.").get_failure_response()
            
        serializer = InternWeeklyReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Weekly review updated successfully.").get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

class InternWeeklyReviewCurrentAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
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
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
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
