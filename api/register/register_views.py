from django.db.models import Q
from rest_framework.views import APIView

from db.organization import Country, Department, District, Organization, State, Zone
from django.utils.decorators import method_decorator
from db.task import InterestGroup
from db.user import Role, User, UserInterests
from utils.response import CustomResponse
from utils.types import OrganizationType
from . import serializers
from .register_helper import get_auth_token
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from mu_celery.task import send_email
from utils.permission import CustomizePermission, JWTUtils
from decouple import config
import requests
from mu_celery.task import onboard_user

DISCORD_CLIENT_ID = config("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = config("DISCORD_CLIENT_SECRET")
FR_DOMAIN_NAME = config("FR_DOMAIN_NAME")


class ConnectDiscordAPI(APIView):
    def get(self, request):
        if not JWTUtils.is_jwt_authenticated(request):
            return CustomResponse(
                general_message="Unauthorized access"
            ).get_failure_response()
        user_id = JWTUtils.fetch_user_id(request)
        token = request.GET.get("code")
        if not token:
            return CustomResponse(
                general_message="Invalid or no token given"
            ).get_failure_response()
        token_url = "https://discord.com/api/oauth2/token"
        redirect_uri = f"{FR_DOMAIN_NAME}/dashboard/connect-discord/"
        data = {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": token,
            "redirect_uri": redirect_uri,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        token_response = requests.post(
            token_url,
            data=data,
            headers=headers,
        )
        access_token = token_response.json().get("access_token")
        if token_response.status_code != 200:
            return CustomResponse(
                general_message="Failed to get access token"
            ).get_failure_response()
        onboard_user.delay(access_token, user_id)
        return CustomResponse(
            general_message="You will be added to the discord server soon"
        ).get_success_response()


class UserInterestAPI(APIView):
    permission_classes = [CustomizePermission]

    def put(self, request):
        if not JWTUtils.is_jwt_authenticated(request):
            return CustomResponse(
                general_message="Unauthorized access"
            ).get_failure_response()
        user_id = JWTUtils.fetch_user_id(request)
        if not (user := cache.get(f"db_user_{user_id}")):
            user = User.objects.filter(id=user_id).first()
        user_interest = UserInterests.objects.filter(user=user).first()
        if not user_interest:
            return CustomResponse(
                general_message="User interests not found"
            ).get_failure_response()
        serializer = serializers.UserInterestSerializer(
            instance=user_interest, data=request.data, context={"user": user}
        )
        if serializer.is_valid():
            serializer.update(user_interest, serializer.validated_data)
            return CustomResponse(
                general_message="Updated interests"
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    def post(self, request):
        if not JWTUtils.is_jwt_authenticated(request):
            return CustomResponse(
                general_message="Unauthorized access"
            ).get_failure_response()
        user_id = JWTUtils.fetch_user_id(request)
        if not (user := cache.get(f"db_user_{user_id}")):
            user = User.objects.filter(id=user_id).first()
        user_interest = UserInterests.objects.filter(user=user).first()
        if user_interest:
            return CustomResponse(
                general_message="User interests already exist"
            ).get_failure_response()
        serializer = serializers.UserInterestSerializer(
            data=request.data, context={"user": user}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Added interests"
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()


class UserRegisterValidateAPI(APIView):
    def put(self, request):
        serialized_user = serializers.RegisterSerializer(data=request.data)

        if not serialized_user.is_valid():
            return CustomResponse(
                general_message=serialized_user.errors
            ).get_failure_response()

        return CustomResponse(response=serialized_user.data).get_success_response()


class RoleAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        roles = Role.objects.all().values("id", "title")
        return CustomResponse(response={"roles": roles}).get_success_response()


class CollegesAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        colleges = Organization.objects.filter(
            org_type=OrganizationType.COLLEGE.value
        ).values("id", "title")

        return CustomResponse(response={"colleges": colleges}).get_success_response()


class DepartmentAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        department_serializer = Department.objects.all().values("id", "title")

        department_serializer_data = serializers.BaseSerializer(
            department_serializer, many=True
        ).data

        return CustomResponse(
            response={"departments": department_serializer_data}
        ).get_success_response()


class CompanyAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        company_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMPANY.value
        ).values("id", "title")

        company_serializer_data = serializers.BaseSerializer(
            company_queryset, many=True
        ).data

        return CustomResponse(
            response={"companies": company_serializer_data}
        ).get_success_response()


class LearningCircleUserViewAPI(APIView):
    def post(self, request):
        muid = request.headers.get("muid")

        user = User.objects.filter(muid=muid).first()

        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()

        serializer = serializers.LearningCircleUserSerializer(user)
        id, muid, full_name, email, phone = serializer.data.values()

        name = full_name

        return CustomResponse(
            response={
                "id": id,
                "muid": muid,
                "name": name,
                "email": email,
                "phone": phone,
            }
        ).get_success_response()


class RegisterDataAPI(APIView):

    def post(self, request):
        data = request.data
        data = {key: value for key, value in data.items() if value}
        # create_user = serializers.UserSerializer(
        #     data=data.get("user"), context={"request": request}
        # )

        create_user = serializers.UserSerializer(
            data=data.pop("user"), context={"request": request}
        )

        if not create_user.is_valid():
            return CustomResponse(message=create_user.errors).get_failure_response()

        user = create_user.save()
        cache.set(f"db_user_{user.muid}", user, timeout=20)
        password = request.data["user"]["password"]
        cache.set(f"flag_register_{user.muid}", True, timeout=5)
        res_data = get_auth_token(user.muid, password)

        response_data = serializers.UserDetailSerializer(user, many=False).data

        send_email.delay(
            response_data,
            "YOUR TICKET TO µFAM IS HERE!",
            ["user_registration.html"],
        )

        res_data["data"] = response_data

        return CustomResponse(response=res_data).get_success_response()


class CountryAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        countries = Country.objects.all()

        serializer = serializers.CountrySerializer(countries, many=True)

        return CustomResponse(
            response={
                "countries": serializer.data,
            }
        ).get_success_response()


class StateAPI(APIView):
    def post(self, request):
        state = State.objects.filter(country_id=request.data.get("country"))
        serializer = serializers.StateSerializer(state, many=True)

        return CustomResponse(
            response={
                "states": serializer.data,
            }
        ).get_success_response()


class DistrictAPI(APIView):
    def post(self, request):
        district = District.objects.filter(zone__state_id=request.data.get("state"))

        serializer = serializers.DistrictSerializer(district, many=True)

        return CustomResponse(
            response={
                "districts": serializer.data,
            }
        ).get_success_response()


class CollegeAPI(APIView):
    def post(self, request):
        org_queryset = Organization.objects.filter(
            Q(org_type=OrganizationType.COLLEGE.value),
            Q(district_id=request.data.get("district")),
        )
        department_queryset = Department.objects.all()

        college_serializer_data = serializers.OrgSerializer(
            org_queryset, many=True
        ).data

        department_serializer_data = serializers.OrgSerializer(
            department_queryset, many=True
        ).data

        return CustomResponse(
            response={
                "colleges": college_serializer_data,
                "departments": department_serializer_data,
            }
        ).get_success_response()


class SchoolAPI(APIView):
    def post(self, request):
        org_queryset = Organization.objects.filter(
            Q(org_type=OrganizationType.SCHOOL.value),
            Q(district_id=request.data.get("district")),
        )

        college_serializer_data = serializers.OrgSerializer(
            org_queryset, many=True
        ).data

        return CustomResponse(
            response={
                "schools": college_serializer_data,
            }
        ).get_success_response()


class CommunityAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        community_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMMUNITY.value
        )

        community_serializer_data = serializers.OrgSerializer(
            community_queryset, many=True
        ).data

        return CustomResponse(
            response={"communities": community_serializer_data}
        ).get_success_response()


class AreaOfInterestAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        aoi_queryset = InterestGroup.objects.all()

        aoi_serializer_data = serializers.AreaOfInterestAPISerializer(
            aoi_queryset, many=True
        ).data

        return CustomResponse(
            response={"aois": aoi_serializer_data}
        ).get_success_response()


class UserEmailVerificationAPI(APIView):
    def post(self, request):
        user_email = request.data.get("email")

        if user := User.objects.filter(email=user_email).first():
            return CustomResponse(
                general_message="This email already exists", response={"value": True}
            ).get_success_response()
        else:
            return CustomResponse(
                general_message="User email not exist", response={"value": False}
            ).get_success_response()


class UserCountryAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    def get(self, request):
        country = Country.objects.all()

        if country is None:
            return CustomResponse(
                general_message="No data available"
            ).get_success_response()

        country_serializer = serializers.UserCountrySerializer(country, many=True).data

        return CustomResponse(response=country_serializer).get_success_response()


class UserStateAPI(APIView):
    def get(self, request):
        country_name = request.data.get("country")

        country_object = Country.objects.filter(name=country_name).first()

        if country_object is None:
            return CustomResponse(
                general_message="No country data available"
            ).get_success_response()

        state_object = State.objects.filter(country_id=country_object).all()

        if len(state_object) == 0:
            return CustomResponse(
                general_message="No state data available for given country"
            ).get_success_response()

        state_serializer = serializers.UserStateSerializer(state_object, many=True).data

        return CustomResponse(response=state_serializer).get_success_response()


class UserZoneAPI(APIView):
    def get(self, request):
        state_name = request.data.get("state")

        state_object = State.objects.filter(name=state_name).first()

        if state_object is None:
            return CustomResponse(
                general_message="No state data available"
            ).get_success_response()

        zone_object = Zone.objects.filter(state_id=state_object).all()

        if len(zone_object) == 0:
            return CustomResponse(
                general_message="No zone data available for given country"
            ).get_success_response()

        zone_serializer = serializers.UserZoneSerializer(zone_object, many=True).data

        return CustomResponse(response=zone_serializer).get_success_response()


class LocationSearchView(APIView):
    def get(self, request):
        query = request.GET.get("q")
        MAX_RESULTS = 7

        if not query:
            return CustomResponse(
                general_message="Query parameter 'q' is required"
            ).get_failure_response()

        queries = [q.strip() for q in query.split(",")]

        # Building the Q object for the OR-based lookup
        query_filter = Q()
        for q in queries:
            query_filter |= Q(name__icontains=q)
            query_filter |= Q(zone__state__name__icontains=q)
            query_filter |= Q(zone__state__country__name__icontains=q)

        districts = District.objects.filter(query_filter).select_related(
            "zone__state", "zone__state__country"
        )[:MAX_RESULTS]
        all_districts = serializers.LocationSerializer(districts, many=True).data

        return CustomResponse(response=all_districts).get_success_response()
