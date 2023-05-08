import uuid
from datetime import timedelta

import decouple
import requests
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from rest_framework.views import APIView

from api.register.serializers import (
    AreaOfInterestAPISerializer,
    LearningCircleUserSerializer,
    OrgSerializer,
    RegisterSerializer,
    UserDetailSerializer,
)
from db.organization import Organization, Department
from db.task import InterestGroup
from db.user import Role, User, ForgotPassword
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils
from .serializers import UserSerializer


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


class RegisterData(APIView):

    def post(self, request):
        data = request.data
        create_user = RegisterSerializer(
            data=data, context={"request": request})
        if create_user.is_valid():
            user_obj, password = create_user.save()
            auth_domain = decouple.config("AUTH_DOMAIN")
            response = requests.post(
                f"{auth_domain}/api/v1/auth/user-authentication/", data={"muid": user_obj.mu_id, "password": password})
            response = response.json()
            if response.get("statusCode") == 200:
                res_data = response.get("response")
                access_token = res_data.get("accessToken")
                refresh_token = res_data.get("refreshToken")
                send_mail("Congrats, You have been successfully registered in μlearn", f" Your Muid {user_obj.mu_id}",
                          decouple.config("EMAIL_HOST_USER"),
                          [user_obj.email], fail_silently=False)
                return CustomResponse(
                    response={
                        "data": UserDetailSerializer(user_obj, many=False).data,
                        "accessToken": access_token,
                        "refreshToken": refresh_token,
                    }
                ).get_success_response()
            else:
                return CustomResponse(message=response.get("message")).get_failure_response()
        else:
            return CustomResponse(message=create_user.errors, general_message="Invalid fields").get_failure_response()


class RoleAPI(APIView):

    def get(self, request):
        roles = [RoleType.STUDENT.value,
                 RoleType.MENTOR.value, RoleType.ENABLER.value]
        role_serializer = Role.objects.filter(title__in=roles)
        role_serializer_data = OrgSerializer(role_serializer, many=True).data
        return CustomResponse(response={"roles": role_serializer_data}).get_success_response()


class CollegeAPI(APIView):

    def get(self, request):
        org_queryset = Organization.objects.filter(org_type=OrganizationType.COLLEGE.value)
        department_queryset = Department.objects.all()
        college_serializer_data = OrgSerializer(org_queryset, many=True).data
        department_serializer_data = OrgSerializer(
            department_queryset, many=True).data
        return CustomResponse(
            response={"colleges": college_serializer_data,
                      "departments": department_serializer_data}
        ).get_success_response()


class CompanyAPI(APIView):

    def get(self, request):
        company_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMPANY.value)
        company_serializer_data = OrgSerializer(
            company_queryset, many=True).data
        return CustomResponse(response={"companies": company_serializer_data}).get_success_response()


class CommunityAPI(APIView):

    def get(self, request):
        community_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMMUNITY.value)
        community_serializer_data = OrgSerializer(
            community_queryset, many=True).data
        return CustomResponse(response={"communities": community_serializer_data}).get_success_response()


class AreaOfInterestAPI(APIView):

    def get(self, request):
        aoi_queryset = InterestGroup.objects.all()
        aoi_serializer_data = AreaOfInterestAPISerializer(
            aoi_queryset, many=True).data
        return CustomResponse(response={"aois": aoi_serializer_data}).get_success_response()


class ForgotPasswordAPI(APIView):
    def post(self, request):
        muid = request.data.get("muid")
        user = User.objects.filter(mu_id=muid).first()

        if user:
            created_at = DateTimeUtils.get_current_utc_time()
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
            current_time = DateTimeUtils.get_current_utc_time()

            if forget_user.expiry > current_time:
                muid = forget_user.user.mu_id
                return CustomResponse(response={"muid": muid}).get_success_response()
            else:
                forget_user.delete()
                return CustomResponse(general_message="Link is expired").get_failure_response()
            return CustomResponse(general_message="he Token").get_success_response()
        else:
            return CustomResponse(general_message="Invalid Token").get_failure_response()


class ResetPasswordConfirmAPI(APIView):
    def post(self, request, token):
        forget_user = ForgotPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = DateTimeUtils.get_current_utc_time()
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


class UserEmailVerification(APIView):

    def post(self, request):

        user_email = request.data.get('email')
        user = User.objects.filter(email=user_email).first()

        if user:
            return CustomResponse(general_message="This email already exists",
                                  response={"value": True}).get_success_response()
        else:
            return CustomResponse(general_message="User email not exist",
                                  response={"value": False}).get_success_response()


class UserInfo(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_muid = JWTUtils.fetch_muid(request)
        user = User.objects.filter(mu_id=user_muid).first()

        if user is None:
            return CustomResponse(general_message='no user data available').get_failure_response()

        response = UserSerializer(user, many=False).data
        return CustomResponse(response=response).get_success_response()
