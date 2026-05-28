import uuid
from datetime import datetime
import logging

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.renderers import JSONRenderer
from rest_framework.views import APIView

from api.register.register_helper import generate_muid, get_auth_token
from db.company import Company
from db.organization import District, Organization, UserOrganizationLink
from db.task import Level, UserLvlLink, Wallet
from db.user import Role, Socials, User, UserRoleLink, UserSettings
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils

from .serializers import (
    CompanyOnboardingStatusSerializer,
    CompanySignupSerializer,
    CompanyVerificationActionSerializer,
    CompanyVerificationListSerializer,
)
from drf_spectacular.utils import extend_schema
from utils.schema_utils import CustomResponseSerializer

logger = logging.getLogger(__name__)


def _generate_unique_slug(name):
    base_slug = slugify(name)[:90] or "company"
    slug = base_slug
    counter = 1
    while Company.objects.filter(slug=slug).exists():
        suffix = f"-{counter}"
        slug = f"{base_slug[: 100 - len(suffix)]}{suffix}"
        counter += 1
    return slug


def _generate_unique_org_code(name):
    clean_name = "".join(ch for ch in name.upper() if ch.isalnum())
    base_code = (clean_name[:8] or "COMPANY").ljust(8, "X")
    counter = 1
    code = base_code
    while Organization.objects.filter(code=code).exists():
        suffix = str(counter).zfill(4)
        code = f"{base_code[:8]}{suffix}"
        code = code[:12]
        counter += 1
    return code[:12]


def _set_company_links_verified(user, is_verified):
    company_role = Role.objects.filter(title=RoleType.COMPANY.value).first()
    if company_role:
        UserRoleLink.objects.filter(user=user, role=company_role).update(verified=is_verified)

    UserOrganizationLink.objects.filter(
        user=user,
        org__org_type=OrganizationType.COMPANY.value,
    ).update(verified=is_verified)


def _is_company_user(user):
    return UserRoleLink.objects.filter(
        user=user,
        role__title=RoleType.COMPANY.value,
    ).exists()


def _has_company_access(user):
    if _is_company_user(user):
        return True
    return Company.objects.filter(company_user_id=user, deleted_at__isnull=True).exists()


def _get_signup_conflict_response(serializer_errors):
    if "poc_email" in serializer_errors:
        return CustomResponse(
            general_message="A user with this email already exists",
            message={"error_code": "DUPLICATE_POC_EMAIL", "errors": serializer_errors},
        ).get_failure_response(
            status_code=409,
            http_status_code=status.HTTP_409_CONFLICT,
        )

    if "name" in serializer_errors:
        return CustomResponse(
            general_message="Company name already exists",
            message={"error_code": "DUPLICATE_COMPANY_NAME", "errors": serializer_errors},
        ).get_failure_response(
            status_code=409,
            http_status_code=status.HTTP_409_CONFLICT,
        )

    if "poc_phone" in serializer_errors:
        return CustomResponse(
            general_message="A user with this phone number already exists",
            message={"error_code": "DUPLICATE_POC_PHONE", "errors": serializer_errors},
        ).get_failure_response(
            status_code=409,
            http_status_code=status.HTTP_409_CONFLICT,
        )

    return None


class CompanySignupAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    renderer_classes = [JSONRenderer]

    @extend_schema(
        tags=['Dashboard - Company - Onboarding'],
        description="Create Company Signup.",
        request=CompanySignupSerializer,
        responses={200: CompanySignupSerializer},
    )
    def post(self, request):
        serializer = CompanySignupSerializer(data=request.data)
        if not serializer.is_valid():
            conflict_response = _get_signup_conflict_response(serializer.errors)
            if conflict_response:
                return conflict_response
            return CustomResponse(
                general_message="Invalid company signup data",
                message={"error_code": "VALIDATION_ERROR", "errors": serializer.errors},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        company_role = Role.objects.filter(title=RoleType.COMPANY.value).first()
        if not company_role:
            return CustomResponse(
                general_message="Company role is not configured",
                message={"error_code": "COMPANY_ROLE_NOT_FOUND"},
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        slug = _generate_unique_slug(data["name"])
        district = None
        district_id = data.get("district_id")
        if district_id:
            district = District.objects.filter(id=district_id).first()

        try:
            with transaction.atomic():
                user = User.every.create(
                    id=str(uuid.uuid4()),
                    muid=generate_muid(data["poc_name"]),
                    full_name=data["poc_name"].strip(),
                    email=data["poc_email"],
                    mobile=(data.get("poc_phone") or None),
                    password=make_password(data["password"]),
                )

                Wallet.objects.create(user=user, created_by=user, updated_by=user)
                Socials.objects.create(user=user, created_by=user, updated_by=user)
                UserSettings.objects.create(user=user, created_by=user, updated_by=user)

                level = Level.objects.filter(level_order=1).first()
                if level:
                    UserLvlLink.objects.create(
                        user=user,
                        level=level,
                        created_by=user,
                        updated_by=user,
                    )

                UserRoleLink.objects.create(
                    user=user,
                    role=company_role,
                    verified=False,
                    created_by=user,
                )

                organization = Organization.objects.filter(
                    org_type=OrganizationType.COMPANY.value,
                    title__iexact=data["name"],
                ).first()

                if not organization:
                    if not district:
                        raise ValueError(
                            "district_id is required when no matching company organization exists"
                        )
                    organization = Organization.objects.create(
                        id=str(uuid.uuid4()),
                        title=data["name"],
                        code=_generate_unique_org_code(data["name"]),
                        org_type=OrganizationType.COMPANY.value,
                        district=district,
                        created_by=user,
                        updated_by=user,
                    )

                if not UserOrganizationLink.objects.filter(
                    user=user,
                    org=organization,
                ).exists():
                    UserOrganizationLink.objects.create(
                        user=user,
                        org=organization,
                        verified=False,
                        created_by=user,
                    )

                company = Company.objects.create(
                    id=str(uuid.uuid4()),
                    company_user_id=user,
                    name=data["name"],
                    logo=None,
                    description=data.get("description") or "Company onboarding in progress.",
                    industry_sector=data.get("industry_sector") or None,
                    website_link=data.get("website_link") or None,
                    email=data["poc_email"],
                    slug=slug,
                    status="pending_verification",
                    location=data.get("location") or None,
                    legal_name=data.get("legal_name") or None,
                    registration_number=data.get("registration_number") or None,
                    tax_id=data.get("tax_id") or None,
                    company_size=data.get("company_size") or None,
                    linkedin_url=data.get("linkedin_url") or None,
                    verification_document_url=data.get("verification_document_url") or None,
                    verification_requested_at=timezone.now(),
                    updated_by=str(user.id),
                    deleted_at=None,
                    deleted_by=None,
                )
        except IntegrityError:
            return CustomResponse(
                general_message="Company signup failed due to duplicate data",
                message={"error_code": "DUPLICATE_DATA"},
            ).get_failure_response(
                status_code=409,
                http_status_code=status.HTTP_409_CONFLICT,
            )
        except ValueError as exc:
            return CustomResponse(
                general_message=str(exc),
                message={"error_code": "VALIDATION_ERROR"},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Company signup failed for email=%s", data.get("poc_email"))
            error_message = {"error_code": "SIGNUP_FAILED"}
            if settings.DEBUG:
                error_message["debug_error"] = str(exc)
            return CustomResponse(
                general_message="Company signup failed",
                message=error_message,
            ).get_failure_response(
                status_code=500,
                http_status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        auth_response = {}
        try:
            auth_response = get_auth_token(user.muid, data["password"])
        except Exception:
            auth_response = {}

        return CustomResponse(
            general_message="Company registration submitted successfully",
            response={
                "company_id": str(company.id),
                "slug": company.slug,
                "muid": user.muid,
                "status": company.status,
                "auth": auth_response,
            },
        ).get_success_response()


class CompanyOnboardingStatusAPIView(APIView):
    permission_classes = [CustomizePermission]
    renderer_classes = [JSONRenderer]

    @extend_schema(
        tags=['Dashboard - Company - Onboarding'],
        description="Retrieve Company Onboarding Status.",
        responses={200: CompanyOnboardingStatusSerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not _has_company_access(user):
            return CustomResponse(
                general_message="Company role required",
                message={"error_code": "COMPANY_ROLE_REQUIRED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        company = (
            Company.objects.filter(company_user_id=user, deleted_at__isnull=True)
            .order_by("-created_at")
            .first()
        )
        if not company:
            return CustomResponse(
                general_message="Company profile not found",
                message={"error_code": "COMPANY_NOT_FOUND"},
            ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = CompanyOnboardingStatusSerializer(company)
        is_active = company.status == "active"
        return CustomResponse(
            general_message="Company onboarding status fetched successfully",
            response={
                **serializer.data,
                "can_edit_profile": company.status in ("pending_verification", "rejected", "active"),
                "can_access_advanced_features": is_active,
                "next_steps": (
                    ["Wait for admin verification approval"]
                    if company.status == "pending_verification"
                    else ["Update profile details and resubmit verification"]
                    if company.status == "rejected"
                    else ["You have full company dashboard access"]
                    if is_active
                    else []
                ),
            },
        ).get_success_response()


class CompanyVerificationRequestListAPIView(APIView):
    permission_classes = [CustomizePermission]
    renderer_classes = [JSONRenderer]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Company - Onboarding'],
        description="Retrieve Company Verification Request List.",
        responses={200: CompanyVerificationListSerializer},
    )
    def get(self, request):
        queryset = Company.objects.select_related("company_user_id").filter(
            deleted_at__isnull=True
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            valid_statuses = {choice[0] for choice in Company.STATUS_CHOICES}
            if status_filter not in valid_statuses:
                return CustomResponse(
                    general_message="Invalid status filter",
                    message={"error_code": "INVALID_STATUS_FILTER"},
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(status=status_filter)

        date_from = request.query_params.get("dateFrom")
        if date_from:
            try:
                parsed_date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                queryset = queryset.filter(
                    verification_requested_at__date__gte=parsed_date_from
                )
            except ValueError:
                return CustomResponse(
                    general_message="dateFrom must be in YYYY-MM-DD format",
                    message={"error_code": "INVALID_DATE_FROM"},
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST,
                )

        date_to = request.query_params.get("dateTo")
        if date_to:
            try:
                parsed_date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                queryset = queryset.filter(
                    verification_requested_at__date__lte=parsed_date_to
                )
            except ValueError:
                return CustomResponse(
                    general_message="dateTo must be in YYYY-MM-DD format",
                    message={"error_code": "INVALID_DATE_TO"},
                ).get_failure_response(
                    status_code=400,
                    http_status_code=status.HTTP_400_BAD_REQUEST,
                )

        paginated = CommonUtils.get_paginated_queryset(
            queryset.order_by("-created_at"),
            request,
            search_fields=[
                "name",
                "slug",
                "company_user_id__full_name",
                "company_user_id__email",
                "legal_name",
                "registration_number",
            ],
            sort_fields={
                "createdAt": "created_at",
                "status": "status",
                "name": "name",
                "requestedAt": "verification_requested_at",
            },
        )
        serializer = CompanyVerificationListSerializer(paginated["queryset"], many=True)
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated["pagination"],
        )


class CompanyVerificationRequestActionAPIView(APIView):
    permission_classes = [CustomizePermission]
    renderer_classes = [JSONRenderer]

    @role_required([RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Company - Onboarding'],
        description="Partially update Company Verification Request Action.",
        request=CompanyVerificationActionSerializer,
        responses={200: CompanyVerificationActionSerializer},
    )
    def patch(self, request, company_id):
        serializer = CompanyVerificationActionSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Invalid verification action",
                message={"error_code": "VALIDATION_ERROR", "errors": serializer.errors},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )

        action = serializer.validated_data["action"]
        reason = serializer.validated_data.get("reason", "").strip()

        company = Company.objects.filter(id=company_id, deleted_at__isnull=True).first()
        if not company:
            return CustomResponse(
                general_message="Company not found",
                message={"error_code": "COMPANY_NOT_FOUND"},
            ).get_failure_response(
                status_code=404,
                http_status_code=status.HTTP_404_NOT_FOUND,
            )

        reviewer_id = JWTUtils.fetch_user_id(request)
        current_status = company.status

        if action == "approve" and current_status not in (
            "pending_verification",
            "rejected",
        ):
            return CustomResponse(
                general_message="Only pending or rejected company requests can be approved",
                message={"error_code": "INVALID_STATUS_TRANSITION"},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )

        if action == "reject" and current_status != "pending_verification":
            return CustomResponse(
                general_message="Only pending company requests can be rejected",
                message={"error_code": "INVALID_STATUS_TRANSITION"},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            if action == "approve":
                company.status = "active"
                company.verified_at = timezone.now()
                company.verified_by = reviewer_id
                company.rejection_reason = None
                company.updated_by = reviewer_id
                company.save(
                    update_fields=[
                        "status",
                        "verified_at",
                        "verified_by",
                        "rejection_reason",
                        "updated_by",
                        "updated_at",
                    ]
                )
                _set_company_links_verified(company.company_user_id, is_verified=True)
                message = "Company verified successfully"
            else:
                company.status = "rejected"
                company.rejection_reason = reason
                company.verified_by = reviewer_id
                company.verified_at = None
                company.updated_by = reviewer_id
                company.save(
                    update_fields=[
                        "status",
                        "rejection_reason",
                        "verified_by",
                        "verified_at",
                        "updated_by",
                        "updated_at",
                    ]
                )
                _set_company_links_verified(company.company_user_id, is_verified=False)
                message = "Company verification request rejected"

        return CustomResponse(
            general_message=message,
            response={
                "company_id": str(company.id),
                "status": company.status,
                "verified_at": company.verified_at.isoformat() if company.verified_at else None,
                "rejection_reason": company.rejection_reason,
            },
        ).get_success_response()


class CompanyVerificationResubmitAPIView(APIView):
    permission_classes = [CustomizePermission]
    renderer_classes = [JSONRenderer]

    @extend_schema(tags=['Dashboard - Company - Onboarding'], description="Create Company Verification Resubmit.",
        responses={200: CustomResponseSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User not found",
                message={"error_code": "USER_NOT_FOUND"},
            ).get_failure_response(
                status_code=401,
                http_status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not _has_company_access(user):
            return CustomResponse(
                general_message="Company role required",
                message={"error_code": "COMPANY_ROLE_REQUIRED"},
            ).get_failure_response(
                status_code=403,
                http_status_code=status.HTTP_403_FORBIDDEN,
            )

        company = (
            Company.objects.filter(
                company_user_id=user,
                status="rejected",
                deleted_at__isnull=True,
            )
            .order_by("-created_at")
            .first()
        )
        if not company:
            return CustomResponse(
                general_message="No rejected company profile found for resubmission",
                message={"error_code": "COMPANY_NOT_ELIGIBLE"},
            ).get_failure_response(
                status_code=400,
                http_status_code=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            company.status = "pending_verification"
            company.verification_requested_at = timezone.now()
            company.rejection_reason = None
            company.verified_at = None
            company.verified_by = None
            company.updated_by = user_id
            company.save(
                update_fields=[
                    "status",
                    "verification_requested_at",
                    "rejection_reason",
                    "verified_at",
                    "verified_by",
                    "updated_by",
                    "updated_at",
                ]
            )
            _set_company_links_verified(user, is_verified=False)

        return CustomResponse(
            general_message="Company verification request resubmitted successfully",
            response={
                "company_id": str(company.id),
                "status": company.status,
                "verification_requested_at": (
                    company.verification_requested_at.isoformat()
                    if company.verification_requested_at
                    else None
                ),
            },
        ).get_success_response()
