from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.company import Company
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers

class CompanyRegistrationAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Submit a new company registration.",
        request=serializers.CompanyRegisterSerializer,
        responses={200: serializers.CompanyRegisterSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        if Company.objects.filter(company_user_id=user_id).exists():
            return CustomResponse(
                general_message="A company request already exists for your account."
            ).get_failure_response()

        serializer = serializers.CompanyRegisterSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Company registration submitted successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Update or resubmit a pending/rejected company registration.",
        request=serializers.CompanyUpdateSerializer,
        responses={200: serializers.CompanyUpdateSerializer},
    )
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id).first()

        if not company:
            return CustomResponse(
                general_message="No company registration request found for your account."
            ).get_failure_response(status_code=404)

        if company.status == "verified":
            return CustomResponse(
                general_message="Your company is already verified. Please use the profile endpoint to update your details."
            ).get_failure_response()

        serializer = serializers.CompanyUpdateSerializer(
            company, data=request.data, partial=True, context={"user_id": user_id}
        )

        if serializer.is_valid():
        
            if company.status == "rejected":
                serializer.save(status="pending", rejection_reason=None)
                msg = "Company registration updated and resubmitted successfully."
            else:
                serializer.save()
                msg = "Company registration updated successfully."

            return CustomResponse(
                general_message=msg,
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class CompanyStatusAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Check the status of a company registration.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        company = Company.objects.filter(company_user_id=user_id).first()
        if not company:
            return CustomResponse(
                general_message="No company request found for your account."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.CompanyDetailSerializer(company)
        response_data = serializer.data
        response_data["company_id"] = company.id
        
        return CustomResponse(
            response=response_data
        ).get_success_response()

class CompanyProfileAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Retrieve the profile of the authenticated company (creator or approved company mentor).",
        responses={200: serializers.CompanyDetailSerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        
        if not company:
            return CustomResponse(
                general_message="Company profile not found or access denied."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.CompanyDetailSerializer(company)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Update the profile of the authenticated company (creator or approved company mentor).",
        request=serializers.CompanyUpdateSerializer,
        responses={200: serializers.CompanyUpdateSerializer},
    )
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        
        if not company:
            return CustomResponse(
                general_message="Company profile not found or access denied."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.CompanyUpdateSerializer(
            company, data=request.data, partial=True, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Company profile updated successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class CompanyListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="List all companies with filtering.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("industry_sector", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("company_size", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("district_id", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=False, description="Filter by district UUID"),
            OpenApiParameter("state_id", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=False, description="Filter by state UUID"),
            OpenApiParameter("country_id", OpenApiTypes.UUID, OpenApiParameter.QUERY, required=False, description="Filter by country UUID"),
        ],
        responses={200: serializers.CompanyListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        companies = Company.objects.all()

        status = request.query_params.get("status")
        industry_sector = request.query_params.get("industry_sector")
        company_size = request.query_params.get("company_size")
        district_id = request.query_params.get("district_id")
        state_id = request.query_params.get("state_id")
        country_id = request.query_params.get("country_id")

        if status:
            companies = companies.filter(status=status)
        if industry_sector:
            companies = companies.filter(industry_sector=industry_sector)
        if company_size:
            companies = companies.filter(company_size=company_size)
        if district_id:
            companies = companies.filter(district_id=district_id)
        if state_id:
            companies = companies.filter(district__zone__state_id=state_id)
        if country_id:
            companies = companies.filter(district__zone__state__country_id=country_id)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            companies, request, 
            search_fields=["name", "slug", "email", "industry_sector"],
            sort_fields={"name": "name", "status": "status", "created_at": "created_at"}
        )
        
        serializer = serializers.CompanyListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class CompanyDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Get details of a specific company by ID.",
        responses={200: serializers.CompanyDetailSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request, company_id):
        company = Company.objects.filter(id=company_id).first()
        if not company:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.CompanyDetailSerializer(company)
        return CustomResponse(response=serializer.data).get_success_response()

class CompanyVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Verify or reject a company.",
        request=serializers.CompanyVerifySerializer,
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, company_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(id=company_id).first()
        
        if not company:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response(status_code=404)
            
        if company.status == "verified":
            return CustomResponse(
                general_message="Company is already verified."
            ).get_failure_response()
            
        serializer = serializers.CompanyVerifySerializer(
            company, data=request.data, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"Company status updated to {serializer.validated_data.get('status')} successfully."
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class PublicCompanyProfileAPI(APIView):
    permission_classes = []

    @extend_schema(
        tags=['Public - Company'],
        description="Public endpoint to view a company's profile.",
        responses={200: serializers.PublicCompanyProfileSerializer},
    )
    def get(self, request, slug):
        company = Company.objects.filter(slug=slug, status="verified").first()
        if not company:
            return CustomResponse(
                general_message="Company not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.PublicCompanyProfileSerializer(company)
        return CustomResponse(response=serializer.data).get_success_response()


class CompanyAdminSummaryAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Get summary stats for companies for the admin dashboard.",
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        from db.company import Company
        from db.job import CompanyJob
        from db.task import TaskList
        
        companies = Company.objects.all()
        
        data = {
            "total_companies": companies.count(),
            "verified_companies": companies.filter(status="verified").count(),
            "pending_companies": companies.filter(status="pending").count(),
            "rejected_companies": companies.filter(status="rejected").count(),
            "total_jobs": CompanyJob.objects.count(),
            "total_company_tasks": TaskList.objects.filter(
                requested_by__user_role_link_user__role__title=RoleType.COMPANY.value,
                is_deleted=False,
            ).count()
        }
        
        return CustomResponse(response=data).get_success_response()


# ---------------------------------------------------------------------------
# Shared helper — resolves Company for both creator and approved COMPANY_MENTOR
# ---------------------------------------------------------------------------
def _get_company_for_user(user_id):
    """
    Returns the verified Company for a user if they are:
    - the company creator (company_user_id == user_id), OR
    - hold an active COMPANY_MENTOR grant for that company.
    """
    from api.dashboard.mentor.dash_mentor_helper import get_verified_company_for_mentor
    return get_verified_company_for_mentor(user_id)


# ---------------------------------------------------------------------------
# Company Mentor — Nomination endpoints
# ---------------------------------------------------------------------------

class CompanyMentorNominateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Company Mentor"],
        description=(
            "Nominate a platform user as a Company Mentor for your company. "
            "Provide the user's **muid** (e.g. `john-doe@mulearn`). "
            "The user must already be a member of the company's organisation "
            "(i.e. they appear in `UserOrganizationLink` for this company). "
            "Only the verified company creator can nominate. "
            "The nomination enters PENDING state until an admin approves it."
        ),
        request=serializers.CompanyMentorNominateSerializer,
        responses={200: serializers.CompanyMentorListSerializer},
    )
    @role_required([RoleType.COMPANY.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()

        if not company:
            return CustomResponse(
                general_message="You must have a verified company profile to nominate mentors."
            ).get_failure_response(status_code=403)

        serializer = serializers.CompanyMentorNominateSerializer(
            data=request.data,
            context={"user_id": user_id, "company": company},
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        mentor = serializer.save()

        from api.notification.notifications_utils import NotificationUtils
        from db.user import User
        nominator = User.objects.filter(id=user_id).first()
        NotificationUtils.insert_notification(
            user=mentor.user,
            title=f"Company Mentor nomination: {company.name}"[:50],
            description=(
                f"{nominator.full_name if nominator else 'Your company'} nominated you as a "
                f"Company Mentor for {company.name}. Your application is pending approval."
            )[:200],
            button='View',
            url='/mentor/status/',
            created_by=nominator,
        )

        return CustomResponse(
            general_message="User nominated as Company Mentor. Pending approval.",
            response=serializers.CompanyMentorListSerializer(mentor).data,
        ).get_success_response()


class CompanyMentorListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Company Mentor"],
        description="List all Company Mentor nominations for the authenticated company.",
        responses={200: serializers.CompanyMentorListSerializer(many=True)},
    )
    @role_required([RoleType.COMPANY.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()

        if not company:
            return CustomResponse(
                general_message="Verified company profile not found."
            ).get_failure_response(status_code=404)

        org = company.org

        if not org:
            return CustomResponse(
                general_message="Company organization record not found."
            ).get_failure_response(status_code=404)

        from db.user import UserMentor
        mentors = UserMentor.objects.filter(
            mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR,
            org=org,
        ).select_related("user").order_by("-created_at")

        serializer = serializers.CompanyMentorListSerializer(mentors, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

