import datetime

from rest_framework.views import APIView

from db.organization import UserOrganizationLink, Organization
from db.task import TotalKarma, KarmaActivityLog
from db.user import Role, UserRoleLink
from utils.permission import CustomizePermission
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils
from .serializers import StudentLeaderboardSerializer


class StudentsLeaderboard(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        users_total_karma = TotalKarma.objects.all().order_by('-id')[:20]
        if users_total_karma is None:
            return CustomResponse(general_message='No Karma Related data available').get_failure_response()
        data = StudentLeaderboardSerializer(users_total_karma, many=True).data
        return CustomResponse(response=data).get_success_response()


class StudentsMonthlyLeaderboard(APIView):

    def get(self, request):

        today = DateTimeUtils.get_current_utc_time()
        first = today.replace(day=1)
        month = first - datetime.timedelta(days=1)

        year = int(month.strftime('%Y'))
        last_month = int(month.strftime("%m"))
        last_day = int(month.strftime("%d"))

        start_date = str(datetime.date(year, last_month, 1))
        end_date = str(datetime.date(year, last_month, last_day))

        students_leaderboard_dict = {}
        students_leaderboard_list = []

        user_role = Role.objects.filter(title=RoleType.STUDENT.value).first()
        user_role_link = UserRoleLink.objects.filter(role=user_role.id).first()

        if user_role_link is None:
            return CustomResponse(general_message='No Student related data available').get_failure_response()

        monthly_karma = KarmaActivityLog.objects.filter(created_at__range=(start_date, end_date))

        if monthly_karma.first() is None:
            return CustomResponse(general_message='No karma available for last month').get_failure_response()

        for user in monthly_karma:
            user_role_link = UserRoleLink.objects.filter(user=user.created_by).first()

            if user_role_link is None:
                return CustomResponse(general_message='No User role data available').get_failure_response()

            if user_role_link.role.title == RoleType.STUDENT.value:

                user_organization = UserOrganizationLink.objects.filter(user=user.created_by).first()

                name = user.created_by.first_name + ' ' + user.created_by.last_name
                karma = user.karma

                if name in students_leaderboard_dict:
                    students_leaderboard_dict[name]['total_karma'] += karma
                else:
                    students_leaderboard_dict[name] = {
                        'name': name,
                        'total_karma': karma,
                        'code': user_organization.org.code,
                    }

        students_leaderboard_list = list(students_leaderboard_dict.values())

        sorted_students_leaderboard = sorted(students_leaderboard_list, key=lambda i: i['total_karma'], reverse=True)
        sorted_students_leaderboard = sorted_students_leaderboard[:20]

        return CustomResponse(response=sorted_students_leaderboard).get_success_response()


class CollegeLeaderboard(APIView):

    def get(self, request):
        organization_leaderboard_list = []
        organization_leaderboard_dict = {}

        user_role = Role.objects.filter(title=RoleType.STUDENT.value).first()
        user_role_link = UserRoleLink.objects.filter(role=user_role.id).first()
        if user_role_link is None:
            return CustomResponse(general_message='No Student related data available').get_failure_response()

        organization_role_link = UserOrganizationLink.objects.first()
        if organization_role_link is None:
            return CustomResponse(general_message='No organization related data available').get_failure_response()

        organization_type = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value).first()
        if organization_type is None:
            return CustomResponse(general_message='No College related data available').get_failure_response()

        organization_role_link = UserOrganizationLink.objects.all()

        for organization in organization_role_link:

            user_role_link = UserRoleLink.objects.filter(user=organization.user).first()

            if user_role_link is None:
                return CustomResponse(general_message='No User role data available').get_failure_response()

            if user_role_link.role.title == RoleType.STUDENT.value and organization.org.org_type == OrganizationType.COLLEGE.value:

                users_karma = TotalKarma.objects.filter(user=organization.user).first()

                code = organization.org.code
                karma = users_karma.karma

                if code in organization_leaderboard_dict:
                    organization_leaderboard_dict[code]['total_karma'] += karma
                    organization_leaderboard_dict[code]['total_members'] += 1
                else:
                    organization_leaderboard_dict[code] = {
                        'code': code,
                        'total_karma': karma,
                        'total_members': 1,
                        'institution': organization.org.title,
                    }

        organization_leaderboard_list = list(organization_leaderboard_dict.values())

        sorted_organization_leaderboard = sorted(organization_leaderboard_list, key=lambda i: i['total_karma'],
                                                 reverse=True)
        sorted_organization_leaderboard = sorted_organization_leaderboard[:20]

        return CustomResponse(response=sorted_organization_leaderboard).get_success_response()


class CollegeMonthlyLeaderboard(APIView):

    def get(self, request):

        today = DateTimeUtils.get_current_utc_time()
        first = today.replace(day=1)
        month = first - datetime.timedelta(days=1)

        year = int(month.strftime('%Y'))
        last_month = int(month.strftime("%m"))
        last_day = int(month.strftime("%d"))

        start_date = str(datetime.date(year, last_month, 1))
        end_date = str(datetime.date(year, last_month, last_day))

        students_leaderboard_dict = {}
        students_leaderboard_list = []

        user_role = Role.objects.filter(title=RoleType.STUDENT.value).first()
        user_role_link = UserRoleLink.objects.filter(role=user_role.id).first()
        if user_role_link is None:
            return CustomResponse(general_message='No Student related data available').get_failure_response()

        monthly_karma = KarmaActivityLog.objects.filter(created_at__range=(start_date, end_date))
        if monthly_karma.first() is None:
            return CustomResponse(general_message='No karma available for last month').get_failure_response()

        organization_type = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value).first()
        if organization_type is None:
            return CustomResponse(general_message='No College related data available').get_failure_response()

        for user in monthly_karma:
            user_role_link = UserRoleLink.objects.filter(user=user.created_by).first()

            user_organization = UserOrganizationLink.objects.filter(user=user.created_by).first()
            if user_role_link is None:
                return CustomResponse(general_message='No User role data available').get_failure_response()

            if user_role_link.role.title == RoleType.STUDENT.value and user_organization.org.org_type == OrganizationType.COLLEGE.value:

                user_id = user_role_link.user.id
                user_college_code = user_organization.org.code
                user_karma = user.karma

                if user_college_code in students_leaderboard_dict:

                    if user_id not in students_leaderboard_dict[user_college_code]['id']:
                        students_leaderboard_dict[user_college_code]['total_members'] += 1

                    students_leaderboard_dict[user_college_code]['total_karma'] += user_karma

                else:
                    students_leaderboard_dict[user_college_code] = {
                        'id': user_id,
                        'code': user_college_code,
                        'total_karma': user_karma,
                        'total_members': 1,
                        'institution': user_organization.org.title,
                    }

        for college_code, student_leaderboard_dict in students_leaderboard_dict.items():
            student_leaderboard_dict.pop('id')
            students_leaderboard_list.append(student_leaderboard_dict)

        sorted_students_leaderboard = sorted(students_leaderboard_list, key=lambda i: i['total_karma'], reverse=True)
        sorted_students_leaderboard = sorted_students_leaderboard[:20]

        return CustomResponse(response=sorted_students_leaderboard).get_success_response()
