import uuid

from rest_framework import status
from rest_framework.views import APIView

from db.company import Company, CompanyUserLink
from db.user import User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils

from .serializers import CompanyMemberAddSerializer, CompanyMemberSerializer
from drf_spectacular.utils import extend_schema


# ---------------------------------------------------------------------------
# Shared auth helper
# ---------------------------------------------------------------------------

def _get_company_user(request):
    """Return (user, company, error_response). error_response is None on success."""
    try:
        user_id = JWTUtils.fetch_user_id(request)
    except Exception:
        return None, None, CustomResponse(
            general_message="User not found or token invalid.",
            message={"error_code": "USER_NOT_FOUND"},
        ).get_failure_response(status_code=401, http_status_code=status.HTTP_401_UNAUTHORIZED)

    user = User.objects.filter(id=user_id).first()
    if not user:
        return None, None, CustomResponse(
            general_message="User not found.",
            message={"error_code": "USER_NOT_FOUND"},
        ).get_failure_response(status_code=401, http_status_code=status.HTTP_401_UNAUTHORIZED)

    if not UserRoleLink.objects.filter(user=user, role__title=RoleType.COMPANY.value).exists():
        return None, None, CustomResponse(
            general_message="Company role required.",
            message={"error_code": "COMPANY_ROLE_REQUIRED"},
        ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

    company = Company.objects.filter(company_user_id=user, status="active", deleted_at__isnull=True).first()
    if not company:
        return None, None, CustomResponse(
            general_message="No active company found for this user.",
            message={"error_code": "NO_ACTIVE_COMPANY"},
        ).get_failure_response(status_code=403, http_status_code=status.HTTP_403_FORBIDDEN)

    return user, company, None


# ---------------------------------------------------------------------------
# Company: List members
# ---------------------------------------------------------------------------

class CompanyMemberListAPIView(APIView):
    """
    GET /company/members/

    Returns a paginated list of all active members of the company.
    Optional filter: ?role=employee|mentor
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company - Members'],
        description="Retrieve Company Member List.",
        responses={200: CompanyMemberSerializer},
    )
    def get(self, request):
        user, company, err = _get_company_user(request)
        if err:
            return err

        queryset = (
            CompanyUserLink.objects
            .filter(company=company, status="active")
            .select_related(
                "user",
                "user__district",
                "user__wallet_user",
                "user__user_lvl_link_user__level",
            )
            .prefetch_related("user__user_ig_link_user__ig")
            .order_by("-created_at")
        )

        role_filter = request.query_params.get("role")
        if role_filter:
            valid_roles = [r[0] for r in CompanyUserLink.ROLE_CHOICES]
            if role_filter not in valid_roles:
                return CustomResponse(
                    general_message=f"Invalid role filter. Valid values: {valid_roles}",
                    message={"error_code": "INVALID_ROLE_FILTER"},
                ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)
            queryset = queryset.filter(role=role_filter)

        paginated = CommonUtils.get_paginated_queryset(
            queryset=queryset,
            request=request,
            search_fields=["user__full_name", "user__muid"],
            sort_fields={"createdAt": "created_at", "name": "user__full_name"},
            is_pagination=True,
        )

        serializer = CompanyMemberSerializer(list(paginated["queryset"]), many=True)
        return CustomResponse(
            general_message="Members fetched successfully.",
            response={"members": serializer.data, "pagination": paginated["pagination"]},
        ).get_success_response()


# ---------------------------------------------------------------------------
# Company: Add a member
# ---------------------------------------------------------------------------

class CompanyMemberAddAPIView(APIView):
    """
    POST /company/members/add/

    Adds a muLearn user to the company's roster.
    The user must not hold a Company role, and must not already be a member.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company - Members'],
        description="Create Company Member Add.",
        request=CompanyMemberAddSerializer,
        responses={200: CompanyMemberSerializer},
    )
    def post(self, request):
        user, company, err = _get_company_user(request)
        if err:
            return err

        serializer = CompanyMemberAddSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Invalid input.",
                message={"error_code": "VALIDATION_ERROR", "errors": serializer.errors},
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        target_user_id = str(serializer.validated_data["user_id"])
        role = serializer.validated_data["role"]

        target_user = User.objects.filter(id=target_user_id).first()
        if not target_user:
            return CustomResponse(
                general_message="User not found.",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

        # Block adding another company admin as a member
        if UserRoleLink.objects.filter(user=target_user, role__title=RoleType.COMPANY.value).exists():
            return CustomResponse(
                general_message="Company users cannot be added as members.",
                message={"error_code": "COMPANY_ROLE_NOT_ALLOWED"},
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        # Check if already an active member
        existing = CompanyUserLink.objects.filter(company=company, user=target_user).first()
        if existing:
            if existing.status == "active":
                return CustomResponse(
                    general_message="This user is already a member of the company.",
                    message={"error_code": "DUPLICATE_MEMBER"},
                ).get_failure_response(status_code=409, http_status_code=status.HTTP_409_CONFLICT)
            # Re-activate a removed member
            existing.status = "active"
            existing.role = role
            existing.added_by = user
            existing.save(update_fields=["status", "role", "added_by", "updated_at"])
            link = existing
        else:
            link = CompanyUserLink.objects.create(
                id=str(uuid.uuid4()),
                company=company,
                user=target_user,
                role=role,
                status="active",
                added_by=user,
            )

        # Re-fetch with relations for serializer
        link = (
            CompanyUserLink.objects
            .select_related(
                "user", "user__district", "user__wallet_user",
                "user__user_lvl_link_user__level",
            )
            .prefetch_related("user__user_ig_link_user__ig")
            .get(id=link.id)
        )

        return CustomResponse(
            general_message="Member added successfully.",
            response=CompanyMemberSerializer(link).data,
        ).get_success_response()


# ---------------------------------------------------------------------------
# Company: Remove a member (soft delete)
# ---------------------------------------------------------------------------

class CompanyMemberRemoveAPIView(APIView):
    """
    DELETE /company/members/<link_id>/remove/

    Soft-deletes a company member link by setting status='removed'.
    Only the company that owns the link can remove.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Company - Members'], description="Delete Company Member Remove.",
        responses={200: CompanyMemberSerializer},
    )
    def delete(self, request, link_id):
        user, company, err = _get_company_user(request)
        if err:
            return err

        try:
            link = CompanyUserLink.objects.get(id=link_id, company=company)
        except CompanyUserLink.DoesNotExist:
            return CustomResponse(
                general_message="Member link not found.",
                message={"error_code": "MEMBER_NOT_FOUND"},
            ).get_failure_response(status_code=404, http_status_code=status.HTTP_404_NOT_FOUND)

        if link.status == "removed":
            return CustomResponse(
                general_message="Member has already been removed.",
                message={"error_code": "ALREADY_REMOVED"},
            ).get_failure_response(status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST)

        link.status = "removed"
        link.save(update_fields=["status", "updated_at"])

        return CustomResponse(
            general_message="Member removed successfully.",
            response={"link_id": str(link.id), "status": link.status},
        ).get_success_response()
