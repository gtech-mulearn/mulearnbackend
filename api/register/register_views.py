from django.db.models import Q
from rest_framework.views import APIView

from db.organization import Country, Department, District, Organization, State, Zone
from django.utils.decorators import method_decorator
from db.task import InterestGroup
from db.user import Role, User, UserDomains, UserEndgoals
from utils.response import CustomResponse
from utils.types import OrganizationType
from . import serializers
from .register_helper import get_auth_token, verify_google_temp_token, get_auth_token_by_id
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from mu_celery.task import send_email
from utils.permission import CustomizePermission, JWTUtils
from decouple import config
import requests
from mu_celery.task import onboard_user
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s

DISCORD_CLIENT_ID = config("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = config("DISCORD_CLIENT_SECRET")
FR_DOMAIN_NAME = config("FR_DOMAIN_NAME")


class ConnectDiscordAPI(APIView):
    @extend_schema(tags=['Register'], description="Retrieve Connect Discord.",
        responses={200: OpenApiResponse(description="Discord onboard success message")},
    )
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
        redirect_uri = f"{FR_DOMAIN_NAME}/dashboard/connect-discord"
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
        if token_response.status_code != 200:
            # Discord can return a non-JSON error body (e.g. a gateway error page) —
            # check the status before parsing, otherwise .json() can raise and turn
            # a normal failure into an unhandled 500.
            return CustomResponse(
                general_message="Failed to get access token"
            ).get_failure_response()
        access_token = token_response.json().get("access_token")
        onboard_user.delay(access_token, user_id)
        return CustomResponse(
            general_message="You will be added to the discord server soon"
        ).get_success_response()


class UserDomainSelectionAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Register'], description="Create User Domain Selection.",
        responses={200: serializers.UserSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        domains = request.data.get("domains")
        if not domains or not isinstance(domains, list) or not len(domains) > 0:
            return CustomResponse(
                general_message="Domains is required."
            ).get_failure_response(status_code=400)
        try:
            UserDomains.objects.filter(user_id=user_id).delete()
            UserDomains.objects.bulk_create(
                [UserDomains(domain_name=domain, user_id=user_id) for domain in domains]
            )
            return CustomResponse(
                general_message="Domains selected"
            ).get_success_response()
        except Exception as e:
            print("Exception during domain selection:", e)
            return CustomResponse(
                general_message="An unexpected error occured"
            ).get_failure_response(500)


class UserEndgoalSelectionAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Register'], description="Create User Endgoal Selection.",
        responses={200: serializers.UserSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        endgoals = request.data.get("endgoals")
        if not endgoals or not isinstance(endgoals, list) or not len(endgoals) > 0:
            return CustomResponse(
                general_message="Endgoals is required."
            ).get_failure_response(status_code=400)
        try:
            UserEndgoals.objects.filter(user_id=user_id).delete()
            UserEndgoals.objects.bulk_create(
                [
                    UserEndgoals(endgoal_name=endgoal, user_id=user_id)
                    for endgoal in endgoals
                ]
            )
            return CustomResponse(
                general_message="Endgoals selected"
            ).get_success_response()
        except Exception as e:
            print("Exception during endgoal selection:", e)
            return CustomResponse(
                general_message="An unexpected error occured"
            ).get_failure_response(500)


# class UserInterestAPI(APIView):
#     permission_classes = [CustomizePermission]

#     def put(self, request):
#         if not JWTUtils.is_jwt_authenticated(request):
#             return CustomResponse(
#                 general_message="Unauthorized access"
#             ).get_failure_response()
#         user_id = JWTUtils.fetch_user_id(request)
#         if not (user := cache.get(f"db_user_{user_id}")):
#             user = User.objects.filter(id=user_id).first()
#         user_interest = UserInterests.objects.filter(user=user).first()
#         if not user_interest:
#             return CustomResponse(
#                 general_message="User interests not found"
#             ).get_failure_response()
#         serializer = serializers.UserInterestSerializer(
#             instance=user_interest, data=request.data, context={"user": user}
#         )
#         if serializer.is_valid():
#             serializer.update(user_interest, serializer.validated_data)
#             return CustomResponse(
#                 general_message="Updated interests"
#             ).get_success_response()
#         return CustomResponse(general_message=serializer.errors).get_failure_response()

#     def post(self, request):
#         if not JWTUtils.is_jwt_authenticated(request):
#             return CustomResponse(
#                 general_message="Unauthorized access"
#             ).get_failure_response()

#         user_id = JWTUtils.fetch_user_id(request)
#         if not (user := cache.get(f"db_user_{user_id}")):
#             user = User.objects.filter(id=user_id).first()

#         user_interest = UserInterests.objects.filter(user=user).first()
#         if user_interest:
#             return CustomResponse(
#                 general_message="User interests already exist"
#             ).get_failure_response()
#         serializer = serializers.UserInterestSerializer(
#             data=request.data, context={"user": user}
#         )
#         if serializer.is_valid():
#             serializer.save()
#             return CustomResponse(
#                 general_message="Added interests"
#             ).get_success_response()
#         return CustomResponse(general_message=serializer.errors).get_failure_response()


class UnverifiedOrganizationCreateView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Register'],
        description="Create Unverified Organization Create.",
        request=serializers.UnverifiedOrganizationCreateSerializer,
        responses={200: serializers.UnverifiedOrganizationCreateSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serialized_org = serializers.UnverifiedOrganizationCreateSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if not serialized_org.is_valid():
            return CustomResponse(
                general_message=serialized_org.errors
            ).get_failure_response()

        serialized_org.save()
        return CustomResponse(
            general_message="Organization Request Submitted."
        ).get_success_response()


class UserRegisterValidateAPI(APIView):
    @extend_schema(
        tags=['Register'],
        description="Update User Register Validate.",
        request=serializers.RegisterSerializer,
        responses={200: serializers.RegisterSerializer},
    )
    def put(self, request):
        serialized_user = serializers.RegisterSerializer(data=request.data)

        if not serialized_user.is_valid():
            return CustomResponse(
                general_message=serialized_user.errors
            ).get_failure_response()

        return CustomResponse(response=serialized_user.data).get_success_response()


class RoleAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    @extend_schema(tags=['Register'], description="Retrieve Role.",
        responses={200: serializers.RoleSerializer},
    )
    def get(self, request):
        roles = Role.objects.all().values("id", "title")
        return CustomResponse(response={"roles": roles}).get_success_response()


class CollegesAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    @extend_schema(tags=['Register'], description="Retrieve Colleges.",
        responses={200: inline_serializer(
            name='RegisterCollegesResponse',
            fields={'colleges': s.ListField(child=inline_serializer(
                name='RegisterCollegeItem',
                fields={'id': s.CharField(), 'title': s.CharField()},
            ))},
        )},
    )
    def get(self, request):
        colleges = Organization.objects.filter(
            org_type=OrganizationType.COLLEGE.value
        ).values("id", "title")

        return CustomResponse(response={"colleges": colleges}).get_success_response()


class DepartmentAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    @extend_schema(tags=['Register'], description="Retrieve Department.",
        responses={200: serializers.DepartmentSerializer},
    )
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
    @extend_schema(tags=['Register'], description="Retrieve Company.",
        responses={200: inline_serializer(
            name='RegisterCompaniesResponse',
            fields={'companies': s.ListField(child=inline_serializer(
                name='RegisterCompanyItem',
                fields={'id': s.CharField(), 'title': s.CharField()},
            ))},
        )},
    )
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
    @extend_schema(
        tags=['Register'],
        description="Create Learning Circle User View.",
        responses={200: serializers.LearningCircleUserSerializer},
    )
    def post(self, request):
        muid = request.headers.get("muid")

        user = User.objects.filter(muid=muid).first()

        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()

        data = serializers.LearningCircleUserSerializer(user).data

        return CustomResponse(
            response={
                "id": data["id"],
                "muid": data["muid"],
                "name": data["full_name"],
                "email": data["email"],
                "phone": data["mobile"],
            }
        ).get_success_response()


class RegisterDataAPI(APIView):

    @extend_schema(
        tags=['Register'],
        description="Create Register Data.",
        request=serializers.RegisterSerializer,
        responses={200: serializers.UserDetailSerializer},
    )
    def post(self, request):
        from utils.exception import CustomException

        data = request.data.copy()
        data = {key: value for key, value in data.items() if value}

        is_google_signup = False
        temp_token = data.pop("tempToken", None)

        if temp_token:
            # ── Google sign-up path ──────────────────────────────────────────
            try:
                google_data = verify_google_temp_token(temp_token)
            except CustomException as e:
                return CustomResponse(general_message=str(e)).get_failure_response()

            user_data = dict(data.get("user", {}))

            # Only email is forced from Google — client cannot spoof it (B5 / D1)
            user_data["email"] = google_data["email"].strip().lower()

            # full_name comes from the form (editable per D1).
            # Fall back to the Google value if the client didn't send one.
            if not user_data.get("full_name"):
                user_data["full_name"] = google_data["fullName"]

            user_data.pop("password", None)   # no password for Google users
            data["user"] = user_data
            is_google_signup = True

            # B3: idempotent re-issue — if this email already has a NULL-password
            # user it is an orphan from a prior failed attempt; just re-issue tokens.
            # Uses User.every (not User.objects) because the default ActiveUserManager
            # excludes suspended accounts; their emails still occupy the unique constraint
            # and would cause a DB-level IntegrityError on save().
            existing = User.every.filter(email=user_data["email"]).first()
            if existing:
                if existing.password:
                    # Has a real password → was registered via the classic path
                    return CustomResponse(
                        general_message="An account with this email already exists. Please sign in normally."
                    ).get_failure_response()
                if existing.suspended_at:
                    # Suspended Google user — do not re-issue tokens
                    return CustomResponse(
                        general_message="This account has been suspended."
                    ).get_failure_response()
                # Orphan NULL-password user → re-issue tokens without creating a new row
                try:
                    res_data = get_auth_token_by_id(existing.id)
                except CustomException as e:
                    return CustomResponse(general_message=str(e)).get_failure_response()
                res_data["data"] = serializers.UserDetailSerializer(existing).data
                return CustomResponse(response=res_data).get_success_response()
            # ── End Google sign-up path ──────────────────────────────────────

        create_user = serializers.RegisterSerializer(
            data=data, context={"request": request}
        )
        if not create_user.is_valid():
            return CustomResponse(message=create_user.errors).get_failure_response()

        if not is_google_signup:
            password = request.data.get("user", {}).get("password")
            if not password:
                return CustomResponse(
                    general_message="Password is required for email registration."
                ).get_failure_response()

        try:
            # Save user first — commits to DB so the auth service can find
            # the user when we request tokens (avoids uncommitted-row problem).
            user = create_user.save()
            cache.set(f"db_user_{user.muid}", user, timeout=60)

            try:
                if is_google_signup:
                    # NULL password — use TokenVerificationAPI (no password needed)
                    res_data = get_auth_token_by_id(user.id)
                else:
                    res_data = get_auth_token(user.muid, password)
            except CustomException:
                # Auth service failed — clean up the orphaned user
                user.delete()
                raise
        except CustomException as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

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
    @extend_schema(
        tags=['Register'],
        description="Retrieve Country.",
        responses={200: serializers.CountrySerializer},
    )
    def get(self, request):
        countries = Country.objects.all()

        serializer = serializers.CountrySerializer(countries, many=True)

        return CustomResponse(
            response={
                "countries": serializer.data,
            }
        ).get_success_response()


class StateAPI(APIView):
    @extend_schema(
        tags=['Register'],
        description="Create State.",
        responses={200: serializers.StateSerializer},
    )
    def post(self, request):
        state = State.objects.filter(country_id=request.data.get("country"))
        serializer = serializers.StateSerializer(state, many=True)

        return CustomResponse(
            response={
                "states": serializer.data,
            }
        ).get_success_response()


class DistrictAPI(APIView):
    @extend_schema(
        tags=['Register'],
        description="Create District.",
        responses={200: serializers.DistrictSerializer},
    )
    def post(self, request):
        district = District.objects.filter(zone__state_id=request.data.get("state"))

        serializer = serializers.DistrictSerializer(district, many=True)

        return CustomResponse(
            response={
                "districts": serializer.data,
            }
        ).get_success_response()


class CollegeAPI(APIView):
    MAX_RESULTS = 20
    # Large districts (e.g. Bengaluru, Mumbai, Ernakulam) can have 100-200+
    # affiliated colleges, so a district-scoped browse needs a higher cap
    # than the typeahead search, not an unbounded queryset.
    DISTRICT_MAX_RESULTS = 500

    @extend_schema(
        tags=['Register'],
        description="Create College.",
        responses={200: serializers.OrgSerializer},
    )
    def post(self, request):
        district_id = request.data.get("district")
        search_query = request.data.get("search", "").strip()

        # Build base query for colleges in the specified district
        org_queryset = Organization.objects.filter(
            org_type=OrganizationType.COLLEGE.value,
        )

        # Filter by district if provided
        if district_id:
            org_queryset = org_queryset.filter(district_id=district_id)

        # Apply search filter if search query is provided
        if search_query:
            org_queryset = org_queryset.filter(title__icontains=search_query)

        org_queryset = org_queryset.order_by("title")

        # Cap results for a free-text search (typeahead) or a fully unfiltered
        # browse (memory safety, since that spans every college nationwide).
        # A district-scoped browse gets a much higher cap instead of no cap at
        # all, since some districts have 100-200+ affiliated colleges.
        if search_query or not district_id:
            org_queryset = org_queryset[:self.MAX_RESULTS]
        else:
            org_queryset = org_queryset[:self.DISTRICT_MAX_RESULTS]

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
    @extend_schema(
        tags=['Register'],
        description="Create School.",
        responses={200: serializers.OrgSerializer},
    )
    def post(self, request):
        org_queryset = Organization.objects.filter(
            Q(org_type=OrganizationType.SCHOOL.value),
            Q(district_id=request.data.get("district")),
        ).order_by("title")

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
    @extend_schema(
        tags=['Register'],
        description="Retrieve Community.",
        responses={200: serializers.OrgSerializer},
    )
    def get(self, request):
        community_queryset = Organization.objects.filter(
            org_type=OrganizationType.COMMUNITY.value
        ).order_by("title")

        community_serializer_data = serializers.OrgSerializer(
            community_queryset, many=True
        ).data

        return CustomResponse(
            response={"communities": community_serializer_data}
        ).get_success_response()


class AreaOfInterestAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    @extend_schema(
        tags=['Register'],
        description="Retrieve Area Of Interest.",
        responses={200: serializers.AreaOfInterestAPISerializer},
    )
    def get(self, request):
        # Only "active" IGs should be offered as an interest during registration —
        # requested/rejected/cancelled ones aren't real, selectable groups yet.
        aoi_queryset = InterestGroup.objects.filter(status="active")

        aoi_serializer_data = serializers.AreaOfInterestAPISerializer(
            aoi_queryset, many=True
        ).data

        return CustomResponse(
            response={"aois": aoi_serializer_data}
        ).get_success_response()


class UserEmailVerificationAPI(APIView):
    @extend_schema(tags=['Register'], description="Create User Email Verification.",
        responses={200: serializers.UserSerializer},
    )
    def post(self, request):
        user_email = request.data.get("email")

        # User.every (not User.objects/ActiveUserManager) — a suspended user's email
        # still occupies the unique constraint, so it must count as "exists" here too,
        # otherwise registration proceeds and fails later with a DB IntegrityError.
        if user := User.every.filter(email=user_email).first():
            return CustomResponse(
                general_message="This email already exists", response={"value": True}
            ).get_success_response()
        else:
            return CustomResponse(
                general_message="User email not exist", response={"value": False}
            ).get_success_response()


class UserCountryAPI(APIView):
    @method_decorator(cache_page(60 * 10))
    @extend_schema(
        tags=['Register'],
        description="Retrieve User Country.",
        responses={200: serializers.UserCountrySerializer},
    )
    def get(self, request):
        country = Country.objects.all()

        if country is None:
            return CustomResponse(
                general_message="No data available"
            ).get_success_response()

        country_serializer = serializers.UserCountrySerializer(country, many=True).data

        return CustomResponse(response=country_serializer).get_success_response()


class UserStateAPI(APIView):
    @extend_schema(
        tags=['Register'],
        description="Retrieve User State.",
        responses={200: serializers.UserStateSerializer},
    )
    def get(self, request):
        # GET requests carry params in the query string, not a body — request.data
        # is empty for a normal GET call, which made this endpoint always report
        # "No country data available" regardless of what the client sent.
        country_name = request.query_params.get("country")

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
    @extend_schema(
        tags=['Register'],
        description="Retrieve User Zone.",
        responses={200: serializers.UserZoneSerializer},
    )
    def get(self, request):
        # Same GET/query-param fix as UserStateAPI — request.data is empty on GET.
        state_name = request.query_params.get("state")

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
    @extend_schema(
        tags=['Register'],
        description="Retrieve Location Search.",
        responses={200: serializers.LocationSerializer},
    )
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
