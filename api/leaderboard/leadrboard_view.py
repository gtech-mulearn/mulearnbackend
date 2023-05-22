import datetime
from operator import itemgetter

from rest_framework.views import APIView

from db.organization import Organization
from db.task import TotalKarma
from db.user import UserRoleLink
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils
from .serializers import StudentLeaderboardSerializer, StudentMonthlySerializer, CollegeLeaderboardSerializer, \
    CollegeMonthlyLeaderboardSerializer


class StudentsLeaderboard(APIView):

    def get(self, request):
        users_total_karma = TotalKarma.objects.all().order_by('-karma')[:20]
        if users_total_karma is None:
            return CustomResponse(general_message='No Karma Related data available').get_failure_response()
        data = StudentLeaderboardSerializer(users_total_karma, many=True).data
        return CustomResponse(response=data).get_success_response()


class StudentsMonthlyLeaderboard(APIView):

    def get(self, request):

        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(day=1, month=start_date.month % 12 + 1) - datetime.timedelta(days=1)

        user_roles = UserRoleLink.objects.filter(role__title=RoleType.STUDENT.value)

        if user_roles is None:
            return CustomResponse('No student data available').get_failure_response()

        student_monthly_leaderboard = StudentMonthlySerializer(user_roles, many=True,
                                                               context={'start_date': start_date,
                                                                        'end_date': end_date}).data

        student_monthly_leaderboard.sort(key=itemgetter('totalKarma'), reverse=True)
        student_monthly_leaderboard = student_monthly_leaderboard[:20]
        return CustomResponse(response=student_monthly_leaderboard).get_success_response()


class CollegeLeaderboard(APIView):

    def get(self, request):
        organization = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value)
        college_monthly_leaderboard = CollegeLeaderboardSerializer(organization, many=True).data
        college_monthly_leaderboard.sort(key=itemgetter('totalKarma'), reverse=True)
        college_monthly_leaderboard = college_monthly_leaderboard[:20]
        return CustomResponse(response=college_monthly_leaderboard).get_success_response()


class CollegeMonthlyLeaderboard(APIView):

    def get(self, request):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(day=1, month=start_date.month % 12 + 1) - datetime.timedelta(days=1)

        organisation = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value)
        college_monthly_leaderboard = CollegeMonthlyLeaderboardSerializer(organisation, many=True,
                                                                          context={'start_date': start_date,
                                                                                   'end_date': end_date}).data

        college_monthly_leaderboard.sort(key=itemgetter('totalKarma'), reverse=True)
        college_monthly_leaderboard = college_monthly_leaderboard[:20]

        return CustomResponse(response=college_monthly_leaderboard).get_success_response()
