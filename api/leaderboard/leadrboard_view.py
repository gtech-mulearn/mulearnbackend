from utils.utils_views import CustomResponse, get_current_utc_time
from rest_framework.views import APIView

import datetime

from task.models import TotalKarma, TaskList, InterestGroup, UserIgLink, KarmaActivityLog
from organization.models import Organization, UserOrganizationLink
from user.models import User, Role, UserRoleLink


class StudentsLeaderboard(APIView):

    def get(self, request):

        students_leaderboard_dict = {}
        students_leaderboard_list = []

        users_total_karma = TotalKarma.objects.first()
        if users_total_karma is None:
            return CustomResponse(general_message='No Karma Related data avilable').get_failure_response()

        user_role = Role.objects.filter(title='student').first()

        user_role_link = UserRoleLink.objects.filter(role=user_role.id).first()
        if user_role_link is None:
            return CustomResponse(general_message='No Student related data avilable').get_success_response()

        users_total_karma = TotalKarma.objects.all()

        for user_karma in users_total_karma:

            user_role_link = UserRoleLink.objects.filter(user=user_karma.user).first()

            if user_role_link is None:
                return CustomResponse(general_message='No User role data avilable').get_failure_response()

            if user_role_link.role.title == 'Student':

                user_karma = TotalKarma.objects.filter(user=user_role_link.user).first()
                user_organization = UserOrganizationLink.objects.filter(user=user_role_link.user).first()

                students_leaderboard_dict['name'] = user_role_link.user.first_name + ' ' + user_role_link.user.last_name
                students_leaderboard_dict['total_karma'] = user_karma.karma
                students_leaderboard_dict['institution'] = user_organization.org.code

                students_leaderboard_list.append(students_leaderboard_dict)
                students_leaderboard_dict = {}

        sorted_students_leaderboard = sorted(students_leaderboard_list, key=lambda i: i['total_karma'], reverse=True)
        sorted_students_leaderboard = sorted_students_leaderboard[:20]

        return CustomResponse(response=sorted_students_leaderboard).get_success_response()


class StudentsMonthlyLeaderboard(APIView):

    def get(self, request):

        today = datetime.datetime.now()
        first = today.replace(day=1)
        month = first - datetime.timedelta(days=1)

        year = int(month.strftime('%Y'))
        last_month = int(month.strftime("%m"))
        last_day = int(month.strftime("%d"))

        start_date = str(datetime.date(year, last_month, 1))
        end_date = str(datetime.date(year, last_month, last_day))

        students_leaderboard_dict = {}
        students_leaderboard_list = []

        user_role = Role.objects.filter(title='Student').first()
        user_role_link = UserRoleLink.objects.filter(role=user_role.id).first()

        if user_role_link is None:
            return CustomResponse(general_message='No Student related data available').get_success_response()

        monthly_karma = KarmaActivityLog.objects.filter(created_at__range=(start_date, end_date))

        if monthly_karma.first() is None:
            return CustomResponse(general_message='No karma available for last month').get_failure_response()

        for user in monthly_karma:
            user_role_link = UserRoleLink.objects.filter(user=user.created_by).first()

            if user_role_link is None:
                return CustomResponse(general_message='No User role data avilable').get_failure_response()

            if user_role_link.role.title == 'Student':

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

        user_role = Role.objects.filter(title='Student').first()
        user_role_link = UserRoleLink.objects.filter(role=user_role.id).first()
        if user_role_link is None:
            return CustomResponse(general_message='No Student related data avilable').get_success_response()

        organization_role_link = UserOrganizationLink.objects.first()
        if organization_role_link is None:
            return CustomResponse(general_message='No organization related data avilable').get_failure_response()

        organization_role_link = UserOrganizationLink.objects.all()

        for organization in organization_role_link:

            user_role_link = UserRoleLink.objects.filter(user=organization.user).first()

            if user_role_link is None:
                return CustomResponse(general_message='No User role data avilable').get_failure_response()

            if user_role_link.role.title == 'Student' and organization.org.org_type == 'College':

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

        sorted_organization_leaderboard = sorted(organization_leaderboard_list, key=lambda i: i['total_karma'], reverse=True)
        sorted_organization_leaderboard = sorted_organization_leaderboard[:20]

        return CustomResponse(response=sorted_organization_leaderboard).get_success_response()







