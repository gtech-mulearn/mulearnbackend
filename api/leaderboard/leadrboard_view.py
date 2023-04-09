from utils.utils_views import CustomResponse, get_current_utc_time
from rest_framework.views import APIView
from django.db.models import Count, Sum

import datetime
import calendar
import pytz

from task.models import TotalKarma, TaskList, InterestGroup, UserIgLink, KarmaActivityLog
from organization.models import Organization, UserOrganizationLink
from user.models import User, Role, UserRoleLink


class StudentsLeaderboard(APIView):

    def post(self, request):

        students_leaderboard_dict = {}
        students_leaderboard_list = []

        user_karma = TotalKarma.objects.first()
        student_role = Role.objects.filter(title='student').first()

        if user_karma is None:
            return CustomResponse(general_message='Karma Related Datas Not Available').get_failure_response()

        if student_role is None:
            return CustomResponse(general_message='Student Related Datas Not Available').get_failure_response()

        user_karma_details = TotalKarma.objects.all()

        for data in user_karma_details:
            if (Role.objects.filter(created_by=data.user.id).values('title')[0]['title']) == 'student':

                students_leaderboard_dict['name'] = data.user.first_name + " " + data.user.last_name
                students_leaderboard_dict['karma'] = user_karma_details.filter(user_id=data.user.id).values('karma')[0]['karma']
                students_leaderboard_dict['institution'] = Organization.objects.filter(created_by=data.user.id).values('title')[0]['title']

                students_leaderboard_list.append(students_leaderboard_dict)
                students_leaderboard_dict = {}

        sorted_leaderboard = sorted(students_leaderboard_list, key=lambda i: i['karma'], reverse=True)
        sorted_leaderboard = sorted_leaderboard[:20]
        return CustomResponse(response=sorted_leaderboard).get_success_response()


class StudentsMonthlyLeaderboard(APIView):

    def post(self, request):

        today = datetime.datetime.today()
        first = today.replace(day=1)
        month = first - datetime.timedelta(days=1)

        year = int(month.strftime('%Y'))
        last_month = int(month.strftime("%m"))
        last_day = int(month.strftime("%d"))

        start_date = str(datetime.date(year, last_month, 1))
        end_date = str(datetime.date(year, last_month, last_day))

        students_leaderboard_dict = {}
        students_leaderboard_list = []

        monthly_karma = KarmaActivityLog.objects.filter(created_at__range=(start_date, end_date))

        if monthly_karma.first() is None:
            return CustomResponse(general_message='No leaderboard available for last month').get_failure_response()

        user_karma = monthly_karma.values('created_by').annotate(total_karma=Sum('karma')).order_by()

        for data in user_karma:

            first_name = User.objects.filter(id=data['created_by']).values('first_name')[0]['first_name']
            last_name = User.objects.filter(id=data['created_by']).values('last_name')[0]['last_name']

            students_leaderboard_dict['name'] = first_name + " " + last_name
            students_leaderboard_dict['karma'] = data['total_karma']
            students_leaderboard_dict['institution'] = Organization.objects.filter(created_by=data['created_by']).values('title')[0]['title']

            students_leaderboard_list.append(students_leaderboard_dict)
            students_leaderboard_dict = {}

        sorted_leaderboard = sorted(students_leaderboard_list, key=lambda i: i['karma'], reverse=True)
        sorted_leaderboard = sorted_leaderboard[:20]

        return CustomResponse(response=sorted_leaderboard).get_success_response()


