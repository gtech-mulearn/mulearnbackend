from datetime import datetime, timedelta
from uuid import uuid4

import pytz

from user.models import User, Role, UserRoleLink
from task.models import TotalKarma, TaskList, InterestGroup, UserIgLink
from portal.models import Portal, PortalUserAuth, PortalUserMailValidate
from organization.models import Organization, UserOrganizationLink

from decouple import config
from django.core.mail import send_mail
from rest_framework.views import APIView
from utils.utils_views import CustomResponse, get_current_utc_time


# class AddPortal(APIView):
#     def post(self, request):
#         print(request)
#         serializer = PortalSerializer(data=request.data)
#         if serializer.is_valid():
#             obj = serializer.save()
#             return CustomResponse(response={"access_id": obj.access_id}).get_success_response()
#         else:
#             return CustomResponse(has_error=True, status_code=400, message=serializer.errors).get_failure_response()


class MuidValidate(APIView):
    def post(self, request):
        portal_key = request.headers.get('portalKey')
        portal = Portal.objects.filter(portal_key=portal_key).first()
        if portal is None:
            return CustomResponse(has_error=True, status_code=400, message="Invalid Portal").get_failure_response()

        name = request.data.get('name')
        muid = request.data.get('muid')
        user = User.objects.filter(muid=muid).first()

        if user is None:
            return CustomResponse(has_error=True, status_code=400, message="Invalid muid").get_failure_response()
        if not name:
            return CustomResponse(has_error=True, status_code=400, message="Invalid name").get_failure_response()

        mail_token = uuid4()
        expiry_time = get_current_utc_time() + timedelta(seconds=1800)
        PortalUserMailValidate.objects.create(id=uuid4(), portal=portal, user=user, token=mail_token,
                                              expiry=expiry_time)
        DOMAIN_NAME = config('FR_DOMAIN_NAME')
        portal_name = portal.name
        recipient_list = [user.email]
        subject = "Validate mu-id"
        email_from = config('EMAIL_HOST_USER')
        mail_message = f"{user.fullname} have requested to approve muid for {portal_name}.If its you click the following link to authorize {DOMAIN_NAME}/portal/user/authorize/{mail_token}"
        send_mail(subject, mail_message, email_from, recipient_list)

        return CustomResponse(response={"name": user.fullname, "muid": user.muid}).get_success_response()


class UserMailTokenValidation(APIView):

    def post(self, request):
        mail_validation_token = request.data['token']
        utc = pytz.timezone('Asia/Kolkata')
        today_now = datetime.now(utc)
        mail_validation = PortalUserMailValidate.objects.filter(
            token=mail_validation_token).first()
        if mail_validation is None:
            return CustomResponse(has_error=True, message='invalid user token',
                                  status_code=498).get_failure_response()

        expiry_date = mail_validation.expiry
        today = today_now.strftime("%Y-%m-%d %H:%M:%S")
        expiry_date = expiry_date.strftime("%Y-%m-%d %H:%M:%S")

        if expiry_date < today:
            return CustomResponse(has_error=True, message='token is expired',
                                  status_code=498).get_failure_response()

        PortalUserAuth.objects.create(id=uuid4(), portal=mail_validation.portal, user=mail_validation.user,
                                      is_authenticated=True,
                                      created_at=today_now)
        mail_validation.delete()
        return CustomResponse(status_code=200,message="mail token verified").get_success_response()


class GetKarma(APIView):

    def get(self, request):
        portal_key = request.headers.get("portalKey")
        portal = Portal.objects.filter(portal_key=portal_key).first()
        if portal is None:
            return CustomResponse(has_error=True, message='Invalid Portal',
                                  status_code=400).get_failure_response()

        muid = request.data.get("muid")
        if muid is None:
            return CustomResponse(has_error=True, message='muid is None',
                                  status_code=400).get_failure_response()

        students = User.objects.filter(mu_id=muid).first()
        authorized_user = PortalUserAuth.objects.filter(
            user_id=students.id).first()

        if authorized_user and authorized_user.is_authenticated:
            karma = TotalKarma.objects.get(user_id=students.id)
            return CustomResponse(
                response={"muid": muid, "name": students.first_name + students.last_name, "email": students.email,
                          "karma": karma.karma}).get_success_response()
        else:
            return CustomResponse(has_error=True, status_code=400,
                                  message="user not authorized to this portal").get_failure_response()


class UserDetailsApi(APIView):

    def post(self, request, muid):

        user = User.objects.filter(mu_id=muid).first()
        total_karma = TotalKarma.objects.filter(user=user).first()
        user_role = UserRoleLink.objects.filter(user=user).first()
        task_list = TaskList.objects.filter(created_by=user).first()
        interest_group = UserIgLink.objects.filter(created_by=user).first()
        organization = UserOrganizationLink.objects.filter(
            user=user).first()
        # print(interest_group.ig.name)
        if user is None:
            return CustomResponse(has_error=True, message='invalid muid', status_code=498).get_failure_response()
        if total_karma is None:
            return CustomResponse(has_error=True, message='karma related user data not available',
                                  status_code=404).get_failure_response()
        if user_role is None:
            return CustomResponse(has_error=True, message='Roles related data not available for user',
                                  status_code=404).get_failure_response()
        if task_list is None:
            return CustomResponse(has_error=True, message='Task related data not available for user',
                                  status_code=404).get_failure_response()
        if interest_group is None:
            return CustomResponse(has_error=True, message='Interest Group related data not available for user',
                                  status_code=404).get_failure_response()
        if Organization is None:
            return CustomResponse(has_error=True, message='Organization related data not available for user',
                                  status_code=404).get_failure_response()
        return CustomResponse(response={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "karma": total_karma.karma,
            "roles": {
                "main_role": user_role.role.title,
                "authority_roles": None,
            },
            "interest_groups": [interest_group.ig.name.split(',')],
            "tasks": [
                {
                    "task_title": task_list.title,
                    "karma": task_list.karma,
                    "date": task_list.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                },
            ],
            "github_link": None,
            "twitter_link": None,
            "linkedin_link": None,
            "organization": [
                {
                    "name": organization.org.title,
                    "department": None,
                },
            ],
            "profile_pic_link": None
        }).get_success_response()


class GetUnverifiedUsers(APIView):

    def post(self, request):

        non_verified_user = UserRoleLink.objects.filter(verified=False).first()
        if non_verified_user is None:
            return CustomResponse(has_error=True, message='All Users are Verified',
                                  status_code=404).get_failure_response()

        user_data_dict = {}
        user_data_list = []

        non_verified_users = UserRoleLink.objects.filter(verified=False)
        for data in non_verified_users:
            user_data_dict['id'] = data.user.id
            user_data_dict['first_name'] = data.user.first_name
            user_data_dict['last_name'] = data.user.last_name
            user_data_dict['email'] = data.user.email
            user_data_dict['phone'] = data.user.mobile
            user_data_dict['role'] = data.role.title

            user_data_list.append(user_data_dict)
            user_data_dict = {}

        return CustomResponse(response=user_data_list).get_success_response()
