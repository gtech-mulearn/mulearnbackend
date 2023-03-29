import uuid

import decouple
from rest_framework.views import APIView
from api.user.serializers import AreaOfInterestAPISerializer, OrgSerializer, RegisterSerializer, UserDetailSerializer
from organization.models import Department, Organization
from task.models import InterestGroup
from user.models import Role, User, ForgetPassword
from utils.utils_views import CustomResponse, CustomizePermission,get_current_utc_time
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password
import requests
from datetime import datetime, timedelta



class RegisterJWTValidate(APIView):
    authentication_classes = [CustomizePermission]
    print(authentication_classes)

    def get(self, request):
        discord_id = request.auth.get('id', None)
        if User.objects.filter(discord_id=discord_id).exists():
            return CustomResponse(has_error=True, message='You are already registerd',
                                  status_code=400).get_failure_response()
        return CustomResponse(response={'token': True}).get_success_response()


class RegisterData(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        data = request.data
        discord_id = request.auth.get('id', None)
        if User.objects.filter(discord_id=discord_id).exists():
            return CustomResponse(has_error=True, message='user already registered',
                                  status_code=400).get_failure_response()
        create_user = RegisterSerializer(
            data=data, context={'request': request})
        if create_user.is_valid():
            user_obj, user_role_verified = create_user.save()
            if user_role_verified:
                data = {"content": "onboard " + str(user_obj.id)}
                requests.post(decouple.config(
                    'DISCORD_JOIN_WEBHOOK_URL'), data=data)
            return CustomResponse(
                response={"data": UserDetailSerializer(user_obj, many=False).data,
                          "userRoleVerified": user_role_verified}).get_success_response()
        else:
            return CustomResponse(has_error=True, status_code=400, message=create_user.errors).get_failure_response()


class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        roles = ['Student', 'Mentor', 'Enabler']
        role_serializer = Role.objects.filter(title__in=roles)
        role_serializer_data = OrgSerializer(
            role_serializer, many=True).data
        return CustomResponse(response={"roles": role_serializer_data}).get_success_response()


class CollegeAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        org_queryset = Organization.objects.filter(org_type="College")
        department_queryset = Department.objects.all()
        college_serializer_data = OrgSerializer(org_queryset, many=True).data
        department_serializer_data = OrgSerializer(
            department_queryset, many=True).data
        return CustomResponse(response={"colleges": college_serializer_data,
                                        "departments": department_serializer_data}).get_success_response()


class CompanyAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        company_queryset = Organization.objects.filter(org_type="Company")
        company_serializer_data = OrgSerializer(
            company_queryset, many=True).data
        return CustomResponse(response={"companies": company_serializer_data}).get_success_response()


class CommunityAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        community_queryset = Organization.objects.filter(org_type="Community")
        community_serializer_data = OrgSerializer(
            community_queryset, many=True).data
        return CustomResponse(response={"communities": community_serializer_data}).get_success_response()


class AreaOfInterestAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        aoi_queryset = InterestGroup.objects.all()
        aoi_serializer_data = AreaOfInterestAPISerializer(
            aoi_queryset, many=True).data
        return CustomResponse(response={"aois": aoi_serializer_data}).get_success_response()


class ForgotPasswordAPI(APIView):

    def post(self, request):
        email = request.data.get('email')
        user = User.objects.filter(email=email).first()

        if user:
            created_at = get_current_utc_time()
            expiry = created_at + timedelta(seconds=900)  # 15 minutes
            forget_user = ForgetPassword.objects.create(id=uuid.uuid4(), user=user, expiry=expiry,
                                                        created_at=created_at)
            email_host_user = decouple.config('EMAIL_HOST_USER')
            subject = "Password Reset Requested"
            to = [email]
            domain = decouple.config('DOMAIN_NAME')
            message = f"Reset your password with this link {domain}/api/v1/user/reset-password/{forget_user.id}/"
            send_mail(subject, message, email_host_user, to, fail_silently=False)
            return CustomResponse(has_error=False, response={"Forgot Password Email Send Successfully"},
                                  status_code=200).get_success_response()
        else:
            return CustomResponse(has_error=True, response={"User not exist"},
                                  status_code=404).get_failure_response()


class ResetPasswordConfirmAPI(APIView):

    def post(self, request, token):
        forget_user = ForgetPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = get_current_utc_time()
            if forget_user.expiry > current_time:
                new_password = request.data.get('new_password')
                hashed_pwd = make_password(new_password)
                forget_user.user.password = hashed_pwd
                forget_user.user.save()
                forget_user.delete()
                return CustomResponse(response={"New Password Saved Successfully"},
                                      status_code=200).get_success_response()
            else:
                forget_user.delete()
                return CustomResponse(has_error=True, response={"Link is expired"},
                                      status_code=400).get_failure_response()
        else:
            return CustomResponse(has_error=True, response={"User not exist"},
                                  status_code=400).get_failure_response()


class ResetPasswordVerifyTokenAPI(APIView):

    def post(self, request, token):
        forget_user = ForgetPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = get_current_utc_time()
            if forget_user.expiry > current_time:
                muid = forget_user.user.mu_id
                return CustomResponse(response={'muid': muid}, status_code=200).get_success_response()
            else:
                forget_user.delete()
                return CustomResponse(has_error=True, response={"Link is expired"},
                                      status_code=400).get_failure_response()
        else:
            return CustomResponse(has_error=True, response={"User not exist"},
                                  status_code=400).get_failure_response()
