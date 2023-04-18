import uuid
from datetime import timedelta

import decouple
import requests
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from rest_framework.views import APIView

from api.user.serializers import (
    AreaOfInterestAPISerializer,
    LearningCircleUserSerializer,
    OrgSerializer,
    RegisterSerializer,
    UserDetailSerializer,
)
from organization.models import Department, Organization
from task.models import InterestGroup
from user.models import Role, User, ForgotPassword
from utils.utils_views import CustomResponse, CustomizePermission, get_current_utc_time


class LearningCircleUserView(APIView):
    def post(self, request):
        mu_id = request.headers.get("muid")
        user = User.objects.filter(mu_id=mu_id).first()
        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()
        serializer = LearningCircleUserSerializer(user)
        id, mu_id, first_name, last_name, email, phone = serializer.data.values()
        name = f"{first_name}{last_name if last_name else ''}"
        return CustomResponse(
            response={
                "id": id,
                "mu_id": mu_id,
                "name": name,
                "email": email,
                "phone": phone,
            }
        ).get_success_response()


class RegisterJWTValidate(APIView):
    authentication_classes = [CustomizePermission]
    print(authentication_classes)

    def get(self, request):
        discord_id = request.auth.get("id", None)
        if User.objects.filter(discord_id=discord_id).exists():
            return CustomResponse(general_message="You are already registered").get_failure_response()
        return CustomResponse(response={"token": True}).get_success_response()


class RegisterData(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        data = request.data
        discord_id = request.auth.get("id", None)
        if User.objects.filter(discord_id=discord_id).exists():
            return CustomResponse(general_message="user already registered").get_failure_response()
        create_user = RegisterSerializer(data=data, context={"request": request})
        if create_user.is_valid():
            user_obj, user_role_verified = create_user.save()
            if user_role_verified:
                data = {"content": "onboard " + str(user_obj.id)}
                requests.post(decouple.config("DISCORD_JOIN_WEBHOOK_URL"), data=data)
            return CustomResponse(
                response={
                    "data": UserDetailSerializer(user_obj, many=False).data,
                    "userRoleVerified": user_role_verified,
                }
            ).get_success_response()
        else:
            return CustomResponse(general_message=create_user.errors).get_failure_response()


class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        roles = ["Student", "Mentor", "Enabler"]
        role_serializer = Role.objects.filter(title__in=roles)
        role_serializer_data = OrgSerializer(role_serializer, many=True).data
        return CustomResponse(response={"roles": role_serializer_data}).get_success_response()


class CollegeAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        org_queryset = Organization.objects.filter(org_type="College")
        department_queryset = Department.objects.all()
        college_serializer_data = OrgSerializer(org_queryset, many=True).data
        department_serializer_data = OrgSerializer(department_queryset, many=True).data
        return CustomResponse(
            response={"colleges": college_serializer_data, "departments": department_serializer_data}
        ).get_success_response()


class CompanyAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        company_queryset = Organization.objects.filter(org_type="Company")
        company_serializer_data = OrgSerializer(company_queryset, many=True).data
        return CustomResponse(response={"companies": company_serializer_data}).get_success_response()


class CommunityAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        community_queryset = Organization.objects.filter(org_type="Community")
        community_serializer_data = OrgSerializer(community_queryset, many=True).data
        return CustomResponse(response={"communities": community_serializer_data}).get_success_response()


class AreaOfInterestAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        aoi_queryset = InterestGroup.objects.all()
        aoi_serializer_data = AreaOfInterestAPISerializer(aoi_queryset, many=True).data
        return CustomResponse(response={"aois": aoi_serializer_data}).get_success_response()


class ForgotPasswordAPI(APIView):
    def post(self, request):
        muid = request.data.get("muid")
        user = User.objects.filter(mu_id=muid).first()

        if user:
            created_at = get_current_utc_time()
            expiry = created_at + timedelta(seconds=900)  # 15 minutes
            forget_user = ForgotPassword.objects.create(
                id=uuid.uuid4(), user=user, expiry=expiry, created_at=created_at
            )
            email_host_user = decouple.config("EMAIL_HOST_USER")
            subject = "Password Reset Requested"
            to = [user.email]
            domain = decouple.config("FR_DOMAIN_NAME")
            message = f"Reset your password with this link {domain}/user/reset-password?token={forget_user.id}"
            send_mail(subject, message, email_host_user,
                      to, fail_silently=False)
            return CustomResponse(general_message="Forgot Password Email Send Successfully").get_success_response()
        else:
            return CustomResponse(general_message="User not exist").get_failure_response()


class ResetPasswordVerifyTokenAPI(APIView):
    def post(self, request, token):
        forget_user = ForgotPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = get_current_utc_time()
            if forget_user.expiry > current_time:
                muid = forget_user.user.mu_id
                return CustomResponse(response={"muid": muid}).get_success_response()
            else:
                forget_user.delete()
                return CustomResponse(general_message="Link is expired").get_failure_response()
        else:
            return CustomResponse(general_message="Invalid Token").get_failure_response()


class ResetPasswordConfirmAPI(APIView):
    def post(self, request, token):
        forget_user = ForgotPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = get_current_utc_time()
            if forget_user.expiry > current_time:
                new_password = request.data.get("new_password")
                hashed_pwd = make_password(new_password)
                forget_user.user.password = hashed_pwd
                forget_user.user.save()
                forget_user.delete()
                return CustomResponse(general_message="New Password Saved Successfully").get_success_response()
            else:
                forget_user.delete()
                return CustomResponse(general_message="Link is expired").get_failure_response()
        else:
            return CustomResponse(general_message="Invalid Token").get_failure_response()
