import datetime
from datetime import timedelta

from django.db.models import Sum, Q
from rest_framework.views import APIView

from db.organization import Organization
from db.task import TotalKarma
from db.user import UserRoleLink
from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import DateTimeUtils
from .serializers import StudentLeaderboardSerializer, CollegeLeaderboardSerializer, CollegeMonthlyLeaderboardSerializer


class StudentsLeaderboard(APIView):

    def get(self, request):
        users_total_karma = TotalKarma.objects.filter(user__user_role_link_user__role__title='Student').select_related('user').order_by(
            '-karma')[:20]
        if not users_total_karma:
            return CustomResponse(general_message='No Karma Related data available').get_failure_response()
        data = StudentLeaderboardSerializer(users_total_karma, many=True).data
        return CustomResponse(response=data).get_success_response()


class StudentsMonthlyLeaderboard(APIView):
    def get(self, request):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(day=1, month=(start_date.month % 12) + 1) - datetime.timedelta(days=1)

        student_monthly_leaderboard = (
            UserRoleLink.objects.filter(role__title='Student')
            .select_related('user')
            .values(
                'user__id',
                'user__first_name',
                'user__last_name',
            )
            .annotate(
                total_karma=Sum('user__karma_activity_log_user__karma',
                                filter=Q(user__karma_activity_log_user__created_at__range=(start_date, end_date)))
            )
            .order_by('-total_karma')[:20]
        )

        if not student_monthly_leaderboard:
            return CustomResponse(general_message='No student data available').get_failure_response()

        student_monthly_leaderboard = [
            {
                'id': student['user__id'],
                'full_name': f"{student['user__first_name']} {student['user__last_name']}",
                'total_karma': student['total_karma']
            }
            for student in student_monthly_leaderboard
        ]

        return CustomResponse(response=student_monthly_leaderboard).get_success_response()


class CollegeLeaderboard(APIView):

    def get(self, request):
        organizations = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value)
        college_monthly_leaderboard = CollegeLeaderboardSerializer(organizations, many=True).data
        college_monthly_leaderboard.sort(key=lambda x: x['total_karma'], reverse=True)
        college_monthly_leaderboard = college_monthly_leaderboard[:20]
        return CustomResponse(response=college_monthly_leaderboard).get_success_response()


class CollegeMonthlyLeaderboard(APIView):
    def get(self, request):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(day=1, month=start_date.month % 12 + 1) - timedelta(days=1)

        organizations = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value).annotate(
            total_karma=Sum('user_organization_link_org_id__user__karma_activity_log_user__karma',
                            filter=Q(
                                user_organization_link_org_id__user__karma_activity_log_user__created_at__range=(
                                    start_date, end_date)))
        ).order_by('-total_karma')[:20]

        serializer = CollegeMonthlyLeaderboardSerializer(organizations, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
