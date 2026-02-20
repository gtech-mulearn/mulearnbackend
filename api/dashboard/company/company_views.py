from rest_framework.views import APIView

from db.company import Company
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import DateTimeUtils

from .serializers import (
    CompanyReadSerializer,
    CompanySelfUpdateSerializer,
    CompanyAdminUpdateSerializer,
)

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample


class CompanyProfileView(APIView):
    """
    Self-service endpoints for authenticated company users.
    GET    /api/v1/dashboard/company/profile/
    PUT    /api/v1/dashboard/company/profile/
    PATCH  /api/v1/dashboard/company/profile/
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=CompanyReadSerializer,
                description="Company profile retrieved successfully",
            ),
            404: OpenApiResponse(description="Company profile not found"),
            403: OpenApiResponse(description="Access denied. Company role required."),
            401: OpenApiResponse(description="Unauthorized access"),
        },
        summary="Get own company profile",
        description="Retrieves the authenticated company user's own company profile.",
        tags=["Company"],
    )
    @role_required(["Company"])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        company = Company.objects.filter(company_user_id=user_id).first()
        if not company:
            return CustomResponse(
                general_message="Company profile not found"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        if company.status == 'inactive':
            return CustomResponse(
                general_message="Company is inactive. Access denied."
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        serializer = CompanyReadSerializer(company)
        return CustomResponse(
            response=serializer.data,
            general_message="Company profile retrieved successfully",
        ).get_success_response()

    @extend_schema(
        request=CompanySelfUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=CompanyReadSerializer,
                description="Company profile updated successfully",
            ),
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Company profile not found"),
            403: OpenApiResponse(description="Access denied. Company role required."),
            401: OpenApiResponse(description="Unauthorized access"),
        },
        summary="Update own company profile (full)",
        description=(
            "Full update of the authenticated company user's own profile. "
            "Cannot modify: name, slug, status, company_user_id."
        ),
        tags=["Company"],
    )
    @role_required(["Company"])
    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        company = Company.objects.filter(company_user_id=user_id).first()
        if not company:
            return CustomResponse(
                general_message="Company profile not found"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        if company.status == 'inactive':
            return CustomResponse(
                general_message="Company is inactive. Access denied."
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        serializer = CompanySelfUpdateSerializer(
            company, data=request.data, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        serializer.save()
        read_serializer = CompanyReadSerializer(company)
        return CustomResponse(
            response=read_serializer.data,
            general_message="Company profile updated successfully",
        ).get_success_response()

    @extend_schema(
        request=CompanySelfUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=CompanyReadSerializer,
                description="Company profile updated successfully",
            ),
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Company profile not found"),
            403: OpenApiResponse(description="Access denied. Company role required."),
            401: OpenApiResponse(description="Unauthorized access"),
        },
        summary="Partially update own company profile",
        description=(
            "Partial update of the authenticated company user's own profile. "
            "Cannot modify: name, slug, status, company_user_id."
        ),
        tags=["Company"],
    )
    @role_required(["Company"])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        company = Company.objects.filter(company_user_id=user_id).first()
        if not company:
            return CustomResponse(
                general_message="Company profile not found"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        if company.status == 'inactive':
            return CustomResponse(
                general_message="Company is inactive. Access denied."
            ).get_failure_response(
                status_code=403,
                http_status_code=403,
            )

        serializer = CompanySelfUpdateSerializer(
            company, data=request.data, partial=True, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        serializer.save()
        read_serializer = CompanyReadSerializer(company)
        return CustomResponse(
            response=read_serializer.data,
            general_message="Company profile updated successfully",
        ).get_success_response()


class CompanySlugView(APIView):
    """
    Public GET + Admin operations via company slug.
    GET    /api/v1/dashboard/company/<slug>/   (public)
    PUT    /api/v1/dashboard/company/<slug>/   (admin)
    PATCH  /api/v1/dashboard/company/<slug>/   (admin)
    DELETE /api/v1/dashboard/company/<slug>/   (admin)
    """

    def get_authenticators(self):
        request = getattr(self, "request", None)
        if request and request.method == "GET":
            return []
        return [CustomizePermission()]

    def get_permissions(self):
        request = getattr(self, "request", None)
        if request and request.method == "GET":
            return []
        return super().get_permissions()

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=CompanyReadSerializer,
                description="Company profile retrieved successfully",
            ),
            404: OpenApiResponse(description="Company not found"),
        },
        summary="Get company by slug (public)",
        description=(
            "Retrieves public company profile by slug. "
            "No authentication required. Only returns active, non-deleted companies."
        ),
        tags=["Company"],
    )
    def get(self, request, slug):
        company = Company.objects.filter(
            slug=slug,
            status='active',
            deleted_at__isnull=True,
        ).first()

        if not company:
            return CustomResponse(
                general_message="Company not found"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        serializer = CompanyReadSerializer(company)
        return CustomResponse(
            response=serializer.data,
            general_message="Company profile retrieved successfully",
        ).get_success_response()

    @extend_schema(
        request=CompanyAdminUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=CompanyReadSerializer,
                description="Company updated successfully",
            ),
            400: OpenApiResponse(description="Validation error or duplicate name"),
            404: OpenApiResponse(description="Company not found"),
            403: OpenApiResponse(description="Admin access required"),
            401: OpenApiResponse(description="Unauthorized access"),
        },
        examples=[
            OpenApiExample(
                "Admin Update Example",
                value={
                    "name": "Acme Tech Solutions",
                    "status": "blocked",
                    "description": "Updated by admin",
                    "industry_sector": "Technology",
                },
                request_only=True,
            ),
        ],
        summary="Admin update company by slug (full)",
        description=(
            "Full update of any company by slug. Admin only. "
            "Can modify name and status (fields restricted from self-service). "
            "Slug remains immutable."
        ),
        tags=["Company"],
    )
    @role_required([RoleType.ADMIN.value])
    def put(self, request, slug):
        user_id = JWTUtils.fetch_user_id(request)

        company = Company.objects.filter(slug=slug).first()
        if not company:
            return CustomResponse(
                general_message="Company not found"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        serializer = CompanyAdminUpdateSerializer(
            company, data=request.data, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        serializer.save()
        read_serializer = CompanyReadSerializer(company)
        return CustomResponse(
            response=read_serializer.data,
            general_message="Company updated successfully",
        ).get_success_response()

    @extend_schema(
        request=CompanyAdminUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=CompanyReadSerializer,
                description="Company updated successfully",
            ),
            400: OpenApiResponse(description="Validation error or duplicate name"),
            404: OpenApiResponse(description="Company not found"),
            403: OpenApiResponse(description="Admin access required"),
            401: OpenApiResponse(description="Unauthorized access"),
        },
        summary="Admin partial update company by slug",
        description=(
            "Partial update of any company by slug. Admin only. "
            "Can modify name and status (fields restricted from self-service). "
            "Slug remains immutable."
        ),
        tags=["Company"],
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, slug):
        user_id = JWTUtils.fetch_user_id(request)

        company = Company.objects.filter(slug=slug).first()
        if not company:
            return CustomResponse(
                general_message="Company not found"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        serializer = CompanyAdminUpdateSerializer(
            company, data=request.data, partial=True, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        serializer.save()
        read_serializer = CompanyReadSerializer(company)
        return CustomResponse(
            response=read_serializer.data,
            general_message="Company updated successfully",
        ).get_success_response()

    @extend_schema(
        responses={
            200: OpenApiResponse(description="Company deactivated successfully"),
            404: OpenApiResponse(description="Company not found"),
            403: OpenApiResponse(description="Admin access required"),
            401: OpenApiResponse(description="Unauthorized access"),
        },
        summary="Deactivate company by slug (soft delete)",
        description=(
            "Soft-deletes a company by setting status to 'inactive', "
            "recording deleted_at timestamp and deleted_by admin user ID. "
            "Admin only."
        ),
        tags=["Company"],
    )
    @role_required([RoleType.ADMIN.value])
    def delete(self, request, slug):
        user_id = JWTUtils.fetch_user_id(request)

        company = Company.objects.filter(slug=slug).first()
        if not company:
            return CustomResponse(
                general_message="Company not found"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        if company.status == 'inactive':
            return CustomResponse(
                response={
                    "slug": company.slug,
                    "status": company.status,
                    "deleted_at": str(company.deleted_at),
                },
                general_message="Company deactivated successfully",
            ).get_success_response()

        company.status = 'inactive'
        company.deleted_at = DateTimeUtils.get_current_utc_time()
        company.deleted_by_id = user_id
        company.save()

        return CustomResponse(
            response={
                "slug": company.slug,
                "status": company.status,
                "deleted_at": str(company.deleted_at),
            },
            general_message="Company deactivated successfully",
        ).get_success_response()


class CompanyApproveView(APIView):
    """
    Admin-only endpoint to approve a pending company.
    PATCH  /api/v1/dashboard/company/<slug>/approve/
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
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
                                    "example": ["Company approved successfully"],
                                }
                            },
                        },
                        "response": {
                            "type": "object",
                            "properties": {
                                "slug": {"type": "string"},
                                "status": {"type": "string", "example": "active"},
                                "updated_at": {
                                    "type": "string",
                                    "format": "date-time",
                                },
                                "updated_by": {
                                    "type": "string",
                                    "format": "uuid",
                                },
                            },
                        },
                    },
                },
                description="Company approved successfully",
            ),
            404: OpenApiResponse(
                description="Company not found or not in pending status"
            ),
            403: OpenApiResponse(description="Admin access required"),
            401: OpenApiResponse(description="Unauthorized access"),
        },
        summary="Approve a pending company (admin only)",
        description=(
            "Transitions a company's status from 'pending' to 'active'. "
            "Only companies with status='pending' can be approved. "
            "Admin role required. No request body needed."
        ),
        tags=["Company"],
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, slug):
        user_id = JWTUtils.fetch_user_id(request)

        company = Company.objects.filter(
            slug=slug,
            status='pending',
        ).first()

        if not company:
            return CustomResponse(
                general_message="Company not found or not in pending status"
            ).get_failure_response(
                status_code=404,
                http_status_code=404,
            )

        company.status = 'active'
        company.updated_by_id = user_id
        company.save()

        return CustomResponse(
            response={
                "slug": company.slug,
                "status": company.status,
                "updated_at": str(company.updated_at),
                "updated_by": str(company.updated_by_id),
            },
            general_message="Company approved successfully",
        ).get_success_response()
