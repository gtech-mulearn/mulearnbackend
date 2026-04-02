from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from db.company import Company
from db.user import User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType

from .serializers import (
    CompanyProfileCreateUpdateSerializer,
    CompanyProfileSerializer,
    PublicCompanyProfileSerializer,
)


class BaseCompanyProfileView(APIView):
    permission_classes = [CustomizePermission]
    EDITABLE_STATUSES = ("active", "pending_verification", "rejected")

    @staticmethod
    def get_authenticated_user(request):
        try:
            user_id = JWTUtils.fetch_user_id(request)
        except Exception:
            return None
        return User.objects.filter(id=user_id).first()

    @staticmethod
    def is_company_user(user):
        return UserRoleLink.objects.filter(
            user=user,
            role__title=RoleType.COMPANY.value,
        ).exists()

    @staticmethod
    def has_company_access(user):
        if BaseCompanyProfileView.is_company_user(user):
            return True
        return Company.objects.filter(company_user_id=user, deleted_at__isnull=True).exists()

    @staticmethod
    def get_editable_company_for_user(user):
        return (
            Company.objects.filter(
                company_user_id=user,
                status__in=BaseCompanyProfileView.EDITABLE_STATUSES,
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def get_validation_error_response(serializer):
        return CustomResponse(
            general_message="Invalid company profile data",
            message={"error_code": "VALIDATION_ERROR", "errors": serializer.errors},
        ).get_failure_response(
            status_code=400,
            http_status_code=status.HTTP_400_BAD_REQUEST,
        )

    @staticmethod
    def get_conflict_response(error_code, field):
        return CustomResponse(
            general_message=f"Company {field} already exists",
            message={"error_code": error_code},
        ).get_failure_response(
            status_code=409,
            http_status_code=status.HTTP_409_CONFLICT,
        )

    @staticmethod
    def check_name_slug_conflicts(name=None, slug=None, exclude_company_id=None):
        if isinstance(name, str):
            name_qs = Company.objects.filter(name__iexact=name.strip())
            if exclude_company_id:
                name_qs = name_qs.exclude(id=exclude_company_id)
            if name_qs.exists():
                return BaseCompanyProfileView.get_conflict_response(
                    error_code="DUPLICATE_COMPANY_NAME",
                    field="name",
                )

        if isinstance(slug, str):
            slug_qs = Company.objects.filter(slug__iexact=slug.strip())
            if exclude_company_id:
                slug_qs = slug_qs.exclude(id=exclude_company_id)
            if slug_qs.exists():
                return BaseCompanyProfileView.get_conflict_response(
                    error_code="DUPLICATE_SLUG",
                    field="slug",
                )

        return None


class CompanyProfileAPIView(BaseCompanyProfileView):
    def get(self, request):
        user = self.get_authenticated_user(request)
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not self.has_company_access(user):
            return CustomResponse(
                general_message="Company role required",
                message={"error_code": "COMPANY_ROLE_REQUIRED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        company = self.get_editable_company_for_user(user)
        if not company:
            return CustomResponse(
                general_message="No editable company profile found for user",
                message={"error_code": "NO_COMPANY_FOUND"},
            ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompanyProfileSerializer(company)
        return CustomResponse(
            general_message="Company profile fetched successfully",
            response=serializer.data,
        ).get_success_response()

    def post(self, request):
        user = self.get_authenticated_user(request)
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not self.has_company_access(user):
            return CustomResponse(
                general_message="Company role required",
                message={"error_code": "COMPANY_ROLE_REQUIRED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        if Company.objects.filter(company_user_id=user).exists():
            return CustomResponse(
                general_message="Company profile already exists for this user",
                message={"error_code": "COMPANY_ALREADY_EXISTS"},
            ).get_failure_response(
                status_code=409,
                http_status_code=status.HTTP_409_CONFLICT,
            )

        conflict_response = self.check_name_slug_conflicts(
            name=request.data.get("name"),
            slug=request.data.get("slug"),
        )
        if conflict_response:
            return conflict_response

        serializer = CompanyProfileCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.get_validation_error_response(serializer)

        company = serializer.save(
            company_user_id=user,
            status="pending_verification",
            verification_requested_at=timezone.now(),
            updated_by=str(user.id),
            deleted_at=None,
            deleted_by=None,
        )

        return CustomResponse(
            general_message="Company profile created successfully",
            response=CompanyProfileSerializer(company).data,
        ).get_success_response()

    def patch(self, request):
        user = self.get_authenticated_user(request)
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not self.has_company_access(user):
            return CustomResponse(
                general_message="Company role required",
                message={"error_code": "COMPANY_ROLE_REQUIRED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        company = self.get_editable_company_for_user(user)
        if not company:
            return CustomResponse(
                general_message="No editable company profile found for user",
                message={"error_code": "NO_COMPANY_FOUND"},
            ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND,
            )

        if not request.data:
            return CustomResponse(
                general_message="No fields provided for update",
                message={"error_code": "NO_FIELDS_TO_UPDATE"},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )

        conflict_response = self.check_name_slug_conflicts(
            name=request.data.get("name"),
            slug=request.data.get("slug"),
            exclude_company_id=company.id,
        )
        if conflict_response:
            return conflict_response

        serializer = CompanyProfileCreateUpdateSerializer(
            company, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return self.get_validation_error_response(serializer)

        company = serializer.save(updated_by=str(user.id))

        return CustomResponse(
            general_message="Company profile updated successfully",
            response=CompanyProfileSerializer(company).data,
        ).get_success_response()

    def delete(self, request):
        user = self.get_authenticated_user(request)
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not self.has_company_access(user):
            return CustomResponse(
                general_message="Company role required",
                message={"error_code": "COMPANY_ROLE_REQUIRED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        company = self.get_editable_company_for_user(user)
        if not company:
            return CustomResponse(
                general_message="No editable company profile found for user",
                message={"error_code": "NO_COMPANY_FOUND"},
            ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND,
            )

        company.status = "inactive"
        company.deleted_at = timezone.now()
        company.deleted_by = str(user.id)
        company.updated_by = str(user.id)
        company.save(
            update_fields=["status", "deleted_at", "deleted_by", "updated_by", "updated_at"]
        )

        return CustomResponse(
            general_message="Company profile deleted successfully",
            response={
                "company_id": str(company.id),
                "status": company.status,
                "deleted_at": company.deleted_at.isoformat() if company.deleted_at else None,
            },
        ).get_success_response()


class PublicCompanyProfileAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        company = Company.objects.filter(
            slug=slug,
            status="active",
            deleted_at__isnull=True,
        ).first()

        if not company:
            return CustomResponse(
                general_message="Company profile not found",
                message={"error_code": "COMPANY_NOT_FOUND"},
            ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = PublicCompanyProfileSerializer(company)
        return CustomResponse(
            general_message="Public company profile fetched successfully",
            response=serializer.data,
        ).get_success_response()
