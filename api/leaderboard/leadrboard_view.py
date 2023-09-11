from rest_framework.views import APIView

from django.db.models.functions import Concat
from django.db.models import Sum, F, Value

from utils.response import CustomResponse
from utils.types import OrganizationType
from utils.utils import DateTimeUtils

from db.organization import Organization
from db.user import User


class StudentsLeaderboard(APIView):

    def get(self, request):

        students_leaderboard = User.objects.filter(
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value
        ).values(
            total_karma=F('total_karma_user__karma'),
            full_name=Concat(
                F('first_name'),
                Value(' '),
                F('last_name')),
            institution=F('user_organization_link_user__org__title')
        ).order_by(
            '-total_karma'
        )[:20]
        return CustomResponse(response=students_leaderboard).get_success_response()


class StudentsMonthlyLeaderboard(APIView):

    def get(self, request):

        start_date, end_date = DateTimeUtils.get_start_and_end_of_previous_month()

        student_monthly_leaderboard = User.objects.filter(
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            karma_activity_log_user__created_at__range=(
                start_date,
                end_date)
        ).annotate(
            karma=Sum(
                'karma_activity_log_user__karma')
        ).values(
            'id',
            full_name=Concat(
                F('first_name'),
                Value(' '),
                F('last_name')),
            total_karma=F('karma')
        ).order_by(
            '-total_karma'
        )[:20]

        return CustomResponse(response=student_monthly_leaderboard).get_success_response()


class CollegeLeaderboard(APIView):

    def get(self, request):

        college_leaderboard = Organization.objects.filter(
            org_type=OrganizationType.COLLEGE.value
        ).values(
            'code',
            instituion=F('title'),
            total_karma=Sum(
                'user_organization_link_org__user__total_karma_user__karma')
        ).order_by(
            '-total_karma'
        )[:20]

        return CustomResponse(response=college_leaderboard).get_success_response()


class CollegeMonthlyLeaderboard(APIView):

    def get(self, request):

        start_date, end_date = DateTimeUtils.get_start_and_end_of_previous_month()

        college_monthly_leaderboard = Organization.objects.filter(
            user_organization_link_org__user__karma_activity_log_user__created_at__range=(
                start_date,
                end_date),
            org_type=OrganizationType.COLLEGE.value
        ).annotate(
            karma=Sum(
                'user_organization_link_org__user__karma_activity_log_user__karma')
        ).values(
            'code',
            institution=F('title'),
            total_karma=F('karma')
        ).order_by(
            '-total_karma'
        )[:20]

        return CustomResponse(response=college_monthly_leaderboard).get_success_response()
