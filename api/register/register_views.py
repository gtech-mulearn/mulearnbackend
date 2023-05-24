import uuid
from datetime import timedelta

import decouple
import requests
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db.models import Q
from rest_framework.views import APIView

from api.register.serializers import (
    AreaOfInterestAPISerializer,
    LearningCircleUserSerializer,
    OrgSerializer,
    RegisterSerializer,
    UserDetailSerializer,
    CountrySerializer,
    DistrictSerializer,
    StateSerializer, UserDistrictSerializer, UserOrganizationSerializer,
)
from db.organization import Country, District, Organization, Department, State
from db.task import InterestGroup
from db.user import Role, User, ForgotPassword
from db.organization import Country, State, Zone

from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils
from .serializers import UserSerializer, UserCountrySerializer, UserStateSerializer, UserZoneSerializer


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
        create_user = RegisterSerializer(data=data, context={"request": request})

        if create_user.is_valid():
            user_obj, password = create_user.save()

            auth_domain = decouple.config("AUTH_DOMAIN")

            response = requests.post(
                f"{auth_domain}/api/v1/auth/user-authentication/",
                data={"emailOrMuid": user_obj.mu_id, "password": password})
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


class CountryAPI(APIView):

    def get(self, request):
        countries = Country.objects.all()
        serializer = CountrySerializer(countries, many=True)
        return CustomResponse(response={"countries": serializer.data,
                                        }).get_success_response()


class StateAPI(APIView):

    def post(self, request):
        print(request.data.get("country"))
        state = State.objects.filter(country_id=request.data.get("country"))
        serializer = StateSerializer(state, many=True)
        return CustomResponse(response={"states": serializer.data,
                                        }).get_success_response()


class DistrictAPI(APIView):

    def post(self, request):
        district = District.objects.filter(
            zone__state_id=request.data.get("state"))
        serializer = DistrictSerializer(district, many=True)
        return CustomResponse(response={"districts": serializer.data,
                                        }).get_success_response()


class CollegeAPI(APIView):

    def post(self, request):
        org_queryset = Organization.objects.filter(
            Q(org_type=OrganizationType.COLLEGE.value), Q(district_id=request.data.get("district")))
        department_queryset = Department.objects.all()
        college_serializer_data = OrgSerializer(org_queryset, many=True).data
        department_serializer_data = OrgSerializer(
            department_queryset, many=True).data
        return CustomResponse(response={"colleges": college_serializer_data,
                                        "departments": department_serializer_data}).get_success_response()


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
        email_muid = request.data.get('emailOrMuid')
        user = User.objects.filter(
            Q(mu_id=email_muid) | Q(email=email_muid)).first()
        if user:
            created_at = DateTimeUtils.get_current_utc_time()
            expiry = created_at + timedelta(seconds=900)  # 15 minutes
            forget_user = ForgotPassword.objects.create(id=uuid.uuid4(), user=user, expiry=expiry,
                                                        created_at=created_at)
            email_host_user = decouple.config("EMAIL_HOST_USER")
            subject = "Password Reset Requested"
            to = [user.email]
            domain = decouple.config("FR_DOMAIN_NAME")
            message = f"Reset your password with this link {domain}/reset-password?token={forget_user.id}"
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
        else:
            return CustomResponse(general_message="Invalid Token").get_failure_response()


class ResetPasswordConfirmAPI(APIView):
    def post(self, request, token):
        forget_user = ForgotPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = DateTimeUtils.get_current_utc_time()
            if forget_user.expiry > current_time:
                new_password = request.data.get("password")
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
            return CustomResponse(general_message='No user data available').get_failure_response()

        response = UserSerializer(user, many=False).data
        return CustomResponse(response=response).get_success_response()


class UserCountryAPI(APIView):

    def get(self, request):

        country = Country.objects.all()
        if country is None:
            return CustomResponse(general_message="No country data available").get_success_response()
        country_serializer = UserCountrySerializer(country, many=True).data
        return CustomResponse(response=country_serializer).get_success_response()


class UserStateAPI(APIView):

    def get(self, request):
        country_id = request.data.get('countryId')

        state_object = State.objects.filter(country_id=country_id).all()
        if len(state_object) == 0:
            return CustomResponse(general_message='No state data available for given country').get_success_response()

        state_serializer = UserStateSerializer(state_object, many=True).data
        return CustomResponse(response=state_serializer).get_success_response()


class UserZoneAPI(APIView):

    def get(self, request):
        state_id = request.data.get('stateId')

        zone_object = Zone.objects.filter(state_id=state_id).all()
        if len(zone_object) == 0:
            return CustomResponse(general_message='No zone data available for given state').get_success_response()

        zone_serializer = UserStateSerializer(zone_object, many=True).data
        return CustomResponse(response=zone_serializer).get_success_response()


class UserDistrictAPI(APIView):

    def get(self, request):
        zone_id = request.data.get('zoneId')

        district_object = District.objects.filter(zone_id=zone_id).all()
        if len(district_object) == 0:
            return CustomResponse(general_message='No district data available for given zone').get_success_response()

        district_serializer = UserDistrictSerializer(district_object, many=True).data
        return CustomResponse(response=district_serializer).get_success_response()


class UserOrganizationAPI(APIView):

    def get(self, request):
        district_id = request.data.get('districtId')

        organization_object = Organization.objects.filter(district_id=district_id).all()
        if len(organization_object) == 0:
            return CustomResponse(general_message='No organization data available for given zone').get_success_response()

        organization_serializer = UserOrganizationSerializer(organization_object, many=True).data
        return CustomResponse(response=organization_serializer).get_success_response()

