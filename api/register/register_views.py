from django.db.models import Q
from rest_framework.views import APIView
from rest_framework import serializers as drf_serializers

from django.db import transaction
from uuid import uuid4
from django.utils.text import slugify
from db.company import Company
from db.organization import Country, Department, District, Organization, State, Zone
from django.utils.decorators import method_decorator
from db.task import InterestGroup
from db.user import Role, User, UserDomains, UserEndgoals, UserRoleLink
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
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse, OpenApiParameter

DISCORD_CLIENT_ID = config("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = config("DISCORD_CLIENT_SECRET")
FR_DOMAIN_NAME = config("FR_DOMAIN_NAME")


# Inline serializers for Swagger documentation only - NO RUNTIME IMPACT
class EmailVerificationRequestSerializer(drf_serializers.Serializer):
    """Email verification request schema - DOCUMENTATION ONLY"""
    email = drf_serializers.EmailField(required=True, help_text="Email address to verify")


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
        access_token = token_response.json().get("access_token")
        if token_response.status_code != 200:
            return CustomResponse(
                general_message="Failed to get access token"
            ).get_failure_response()
        onboard_user.delay(access_token, user_id)
        return CustomResponse(
            general_message="You will be added to the discord server soon"
        ).get_success_response()


class UserDomainSelectionAPI(APIView):
    permission_classes = [CustomizePermission]

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
        request=serializers.UnverifiedOrganizationCreateSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "statusCode": {"type": "integer", "example": 200},
                        "message": {
                            "type": "object",
                            "properties": {
                                "general": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "example": ["Organization Request Submitted."]
                                }
                            }
                        }
                    }
                },
                description="Organization creation request submitted successfully"
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Unauthorized - Invalid or missing Bearer token"),
        },
        examples=[
            OpenApiExample(
                "College Organization",
                value={
                    "title": "Sample College of Engineering",
                    "org_type": "College",
                    "graduation_year": 2024,
                    "department": "<department-uuid>"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Company Organization",
                value={
                    "title": "Tech Solutions Inc",
                    "org_type": "Company"
                },
                request_only=True,
            ),
        ],
        summary="Submit unverified organization creation request",
        description="""
        Submit a request to create an unverified organization.
        
        **Authentication Required:** Bearer token (JWT)
        
        **Supported Organization Types:**
        - College (requires graduation_year and department)
        - Company
        - Community
        - School
        
        **Note:** Request will be reviewed before approval.
        """,
        tags=["Registration"],
    )
    def post(self, request):
        # NO LOGIC MODIFIED - Documentation only
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


class CompanyCreateView(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        request=serializers.CompanyCreateSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "statusCode": {"type": "integer", "example": 200},
                        "message": {
                            "type": "object",
                            "properties": {
                                "general": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "example": ["Company created successfully"]
                                }
                            }
                        },
                        "response": {
                            "type": "object",
                            "properties": {
                                "company_id": {"type": "string", "format": "uuid"},
                                "name": {"type": "string"},
                                "slug": {"type": "string"}
                            }
                        }
                    }
                },
                description="Company created successfully"
            ),
            400: OpenApiResponse(description="Validation error or company already exists"),
            401: OpenApiResponse(description="Unauthorized - Invalid or missing Bearer token"),
        },
        examples=[
            OpenApiExample(
                "Company Creation Example",
                value={
                    "name": "TechCorp Solutions",
                    "description": "A leading technology solutions provider",
                    "industry_sector": "Information Technology",
                    "website_link": "https://techcorp.example.com",
                    "email": "contact@techcorp.example.com",
                    "location": "Bangalore, Karnataka, India"
                },
                request_only=True,
            ),
        ],
        summary="Create a new company",
        description="""
        Creates a new company profile for the authenticated user.
        
        **Authentication Required:** Bearer token (JWT)
        
        **Business Logic:**
        - Validates that the user doesn't already have a company
        - Generates a unique slug from the company name
        - Creates company record in database
        - Assigns 'company' role to the user
        - Returns company details including generated ID and slug
        
        **Note:** Only one company per user is allowed.
        """,
        tags=["Registration"],
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        serializer = serializers.CompanyCreateSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        validated_data = serializer.validated_data
        name = validated_data.get("name")
        description = validated_data.get("description")

        with transaction.atomic():
            # 1. Check if company already exists for user
            if Company.objects.filter(company_user_id=user_id).exists():
                return CustomResponse(
                    general_message="Company already exists for this user"
                ).get_failure_response()

            # 2. Generate unique slug
            base_slug = slugify(name)
            slug = base_slug
            counter = 1

            while Company.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            # 3. Create company via ORM
            company = Company.objects.create(
                id=str(uuid4()),
                company_user_id=user_id,
                name=name,
                description=description,
                industry_sector=validated_data.get("industry_sector"),
                website_link=validated_data.get("website_link"),
                email=validated_data.get("email"),
                location=validated_data.get("location"),
                slug=slug,
                status='pending',
            )

            # 4. Assign company role
            company_role_title = "Company"
            company_role = Role.objects.filter(title=company_role_title).first()

            if not company_role:
                company_role = Role.objects.create(
                    id=str(uuid4()),
                    title=company_role_title,
                    created_by_id=user_id,
                    updated_by_id=user_id,
                )

            UserRoleLink.objects.create(
                user_id=user_id,
                role_id=company_role.id,
                created_by_id=user_id,
                verified=True,
            )

        return CustomResponse(
            response={
                "company_id": company.id,
                "name": company.name,
                "slug": company.slug,
            },
            general_message="Company created successfully",
        ).get_success_response()




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

    @extend_schema(
        request=serializers.RegisterSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "statusCode": {"type": "integer", "example": 200},
                        "response": {
                            "type": "object",
                            "properties": {
                                "accessToken": {"type": "string", "description": "JWT access token"},
                                "refreshToken": {"type": "string", "description": "JWT refresh token"},
                                "data": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "string", "format": "uuid"},
                                        "muid": {"type": "string", "description": "Unique muLearn ID"},
                                        "email": {"type": "string", "format": "email"},
                                        "full_name": {"type": "string"},
                                        "role": {"type": "string", "nullable": True}
                                    }
                                }
                            }
                        }
                    }
                },
                description="User registered successfully with authentication tokens"
            ),
            400: OpenApiResponse(description="Validation error"),
        },
        examples=[
            OpenApiExample(
                "Student Registration",
                value={
                    "user": {
                        "full_name": "John Doe",
                        "email": "john.doe@example.com",
                        "password": "SecurePass123!",
                        "dob": "2000-01-15",
                        "gender": "Male",
                        "role": "<role-uuid>",
                        "district": "<district-uuid>",
                        "area_of_interest": ["<ig-uuid-1>", "<ig-uuid-2>"]
                    },
                    "referral": {
                        "muid": "MENTOR123"
                    }
                },
                request_only=True,
            ),
        ],
        summary="Register a new user",
        description="""
        Register a new user in the muLearn platform.
        
        **No Authentication Required**
        
        **Process:**
        - Creates user account with hashed password
        - Generates unique µID (muid)
        - Creates wallet, socials, and settings
        - Assigns role and interest groups
        - Sends welcome email asynchronously
        - Returns authentication tokens (access + refresh)
        
        **Optional Fields:**
        - `referral` - Can include either `muid` (referrer's µID) or `invite_code`
        - `integration` - For KKEM integration (param + title)
        
        **Note:** Empty values are filtered out before processing.
        """,
        tags=["Registration"],
    )
    def post(self, request):
        # NO LOGIC MODIFIED - Documentation only
        data = request.data
        data = {key: value for key, value in data.items() if value}

        create_user = serializers.RegisterSerializer(
            data=data, context={"request": request}
        )
        if not create_user.is_valid():
            return CustomResponse(message=create_user.errors).get_failure_response()

        user = create_user.save()
        cache.set(f"db_user_{user.muid}", user, timeout=60)
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
    MAX_RESULTS = 20

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

        # Limit results to prevent memory issues
        org_queryset = org_queryset[:self.MAX_RESULTS]

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
    @extend_schema(
        request=EmailVerificationRequestSerializer,
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "properties": {
                        "statusCode": {"type": "integer", "example": 200},
                        "message": {
                            "type": "object",
                            "properties": {
                                "general": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            }
                        },
                        "response": {
                            "type": "object",
                            "properties": {
                                "value": {
                                    "type": "boolean",
                                    "description": "true if email exists, false otherwise"
                                }
                            }
                        }
                    }
                },
                description="Email verification result"
            ),
        },
        examples=[
            OpenApiExample(
                "Check Email",
                value={"email": "user@example.com"},
                request_only=True,
            ),
            OpenApiExample(
                "Email Exists",
                value={
                    "statusCode": 200,
                    "message": {"general": ["This email already exists"]},
                    "response": {"value": True}
                },
                response_only=True,
            ),
            OpenApiExample(
                "Email Available",
                value={
                    "statusCode": 200,
                    "message": {"general": ["User email not exist"]},
                    "response": {"value": False}
                },
                response_only=True,
            ),
        ],
        summary="Check if email already exists",
        description="""
        Verify if an email address is already registered.
        
        **No Authentication Required**
        
        **Returns:**
        - `value: true` - Email already exists (cannot register)
        - `value: false` - Email available (can register)
        
        **Use Case:** Form validation during registration to prevent duplicate emails.
        """,
        tags=["Registration"],
    )
    def post(self, request):
        # NO LOGIC MODIFIED - Documentation only
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
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Search query (comma-separated for multiple terms). Searches district, state, and country names.",
                examples=[
                    OpenApiExample("Single term", value="Bangalore"),
                    OpenApiExample("Multiple terms", value="Bangalore, Karnataka"),
                ]
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=serializers.LocationSerializer(many=True),
                description="List of matching locations (max 7 results)"
            ),
            400: OpenApiResponse(description="Query parameter 'q' is required"),
        },
        examples=[
            OpenApiExample(
                "Location Results",
                value=[
                    {
                        "id": "uuid-example-1",
                        "location": "Bangalore Urban, Karnataka, India"
                    },
                    {
                        "id": "uuid-example-2",
                        "location": "Bangalore Rural, Karnataka, India"
                    }
                ],
                response_only=True,
            ),
        ],
        summary="Search for locations",
        description="""
        Search for districts by name, state, or country.
        
        **No Authentication Required**
        
        **Search Behavior:**
        - Case-insensitive partial matching
        - Searches across district, state, and country names
        - Supports comma-separated multiple terms (OR logic)
        - Returns maximum 7 results
        
        **Use Case:** Location autocomplete during registration
        """,
        tags=["Registration"],
    )
    def get(self, request):
        # NO LOGIC MODIFIED - Documentation only
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
