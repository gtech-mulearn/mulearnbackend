from datetime import timedelta
from uuid import uuid4

import pytz
from decouple import config
from django.core.mail import send_mail
from rest_framework.views import APIView

from db.organization import Organization, UserOrganizationLink
from db.portal import Portal, PortalUserAuth, PortalUserMailValidate
from db.task import TotalKarma, TaskList, UserIgLink
from db.user import User, UserRoleLink
from utils.response import CustomResponse
from utils.utils import DateTimeUtils


# class AddPortal(APIView):
#     def post(self, request):
#         print(request)
#         serializer = PortalSerializer(data=request.data)
#         if serializer.is_valid():
#             obj = serializer.save()
#             return CustomResponse(response={"access_id": obj.access_id}).get_success_response()
#         else:
#             return CustomResponse(has_error=True, status_code=400, message=serializer.errors).get_failure_response()


class MuidValidateAPI(APIView):
    def post(self, request):
        portal_key = request.headers.get("portalKey")
        portal = Portal.objects.filter(portal_key=portal_key).first()
        if portal is None:
            return CustomResponse(general_message="Invalid Portal").get_failure_response()

        name = request.data.get("name")
        muid = request.data.get("muid")
        user = User.objects.filter(mu_id=muid).first()

        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()
        if not name:
            return CustomResponse(general_message="Invalid name").get_failure_response()

        mail_token = uuid4()
        expiry_time = DateTimeUtils.get_current_utc_time() + timedelta(seconds=1800)
        PortalUserMailValidate.objects.create(
            id=uuid4(),
            portal=portal,
            user=user,
            token=mail_token,
            expiry=expiry_time,
            created_by=user,
            created_at=DateTimeUtils.get_current_utc_time(),
        )
        DOMAIN_NAME = config("FR_DOMAIN_NAME")
        portal_name = portal.name
        recipient_list = [user.email]
        subject = "Validate mu-id"
        email_from = config("EMAIL_HOST_USER")
        name = user.first_name + (user.last_name if user.last_name else "")
        mail_message = f"{name} have requested to approve muid for {portal_name}.If its you click the following link to authorize {DOMAIN_NAME}/portal/user/authorize/{mail_token}"
        send_mail(subject, mail_message, email_from, recipient_list)
        return CustomResponse(response={"name": name, "muid": user.mu_id}).get_success_response()


class UserMailTokenValidationAPI(APIView):
    def post(self, request):
        mail_validation_token = request.data["token"]
        utc = pytz.timezone("Asia/Kolkata")
        today_now = DateTimeUtils.get_current_utc_time()
        mail_validation = PortalUserMailValidate.objects.filter(token=mail_validation_token).first()
        if mail_validation is None:
            return CustomResponse(general_message="invalid user token").get_failure_response(status_code=498)

        expiry_date = mail_validation.expiry
        today = DateTimeUtils.get_current_utc_time()

        if expiry_date < today:
            return CustomResponse(general_message="token is expired").get_failure_response(status_code=498)

        PortalUserAuth.objects.create(
            id=uuid4(),
            portal=mail_validation.portal,
            user=mail_validation.user,
            is_authenticated=True,
            created_by=mail_validation.user,
            created_at=DateTimeUtils.get_current_utc_time(),
        )
        mail_validation.delete()
        return CustomResponse(general_message="mail token verified").get_success_response()


class GetKarmaAPI(APIView):
    def get(self, request):
        portal_key = request.headers.get("portalKey")
        portal = Portal.objects.filter(portal_key=portal_key).first()
        if portal is None:
            return CustomResponse(general_message="Invalid Portal").get_failure_response()

        muid = request.data.get("muid")

        if muid is None:
            return CustomResponse(general_message="muid is None").get_failure_response()

        students = User.objects.filter(mu_id=muid).first()
        authorized_user = PortalUserAuth.objects.filter(user_id=students.id).first()

        if authorized_user and authorized_user.is_authenticated:
            karma = TotalKarma.objects.get(user_id=students.id)
            return CustomResponse(
                response={
                    "muid": muid,
                    "name": students.first_name + students.last_name,
                    "email": students.email,
                    "karma": karma.karma,
                }
            ).get_success_response()
        else:
            return CustomResponse(general_message="user not authorized to this portal").get_failure_response()


class UserDetailsApi(APIView):
    def get(self, request, muid):
        user = User.objects.filter(mu_id=muid).first()
        total_karma = TotalKarma.objects.filter(user=user).first()
        user_role = UserRoleLink.objects.filter(user=user).first()
        task_list = TaskList.objects.filter(created_by=user).first()

        interest_group = UserIgLink.objects.filter(created_by=user).all()
        organization = UserOrganizationLink.objects.filter(user=user).first()
        igname = []
        for i in interest_group:
            igname = igname + [i.ig.name]
        if user is None:
            return CustomResponse(general_message="invalid muid").get_failure_response(status_code=498)
        if total_karma is None:
            return CustomResponse(general_message="karma related user data not available").get_failure_response()
        if user_role is None:
            return CustomResponse(general_message="Roles related data not available for user").get_failure_response()
        if task_list is None:
            return CustomResponse(general_message="Task related data not available for user").get_failure_response()
        if interest_group is None:
            return CustomResponse(
                general_message="Interest Group related data not available for user"
            ).get_failure_response()
        if Organization is None:
            return CustomResponse(
                general_message="Organization related data not available for user"
            ).get_failure_response()
        return CustomResponse(
            response={
                "firstName": user.first_name,
                "lastName": user.last_name,
                "karma": total_karma.karma,
                "roles": {
                    "mainRole": user_role.role.title,
                    "authorityRoles": None,
                },
                "interest_groups": igname,
                "tasks": [
                    {
                        "taskTitle": task_list.title,
                        "karma": task_list.karma,
                        "date": task_list.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                ],
                "githubLink": None,
                "twitterLink": None,
                "linkedinLink": None,
                "organization": [
                    {
                        "name": organization.org.title if organization else None,
                        "department": None,
                    },
                ],
                "profilePicLink": None,
            }
        ).get_success_response()


class GetUnverifiedUsers(APIView):
    def get(self, request):
        non_verified_user = UserRoleLink.objects.filter(verified=False).first()
        if non_verified_user is None:
            return CustomResponse(general_message="All Users are Verified").get_failure_response()

        user_data_dict = {}
        user_data_list = []

        non_verified_users = UserRoleLink.objects.filter(verified=False)
        for data in non_verified_users:
            user_data_dict["id"] = data.user.id
            user_data_dict["first_name"] = data.user.first_name
            user_data_dict["last_name"] = data.user.last_name
            user_data_dict["email"] = data.user.email
            user_data_dict["phone"] = data.user.mobile
            user_data_dict["role"] = data.role.title

            user_data_list.append(user_data_dict)
            user_data_dict = {}

        return CustomResponse(response=user_data_list).get_success_response()
