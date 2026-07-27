from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.company import Company, CompanyAdminLink
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers


def is_company_owner_or_admin(user_id, company):
    """
    Addon §6.5 — true if `user_id` is the company's true owner OR a delegate
    who has ACCEPTED their invite (CompanyAdminLink). A pending/declined/
    revoked link grants no authority. Delegates cannot create further
    delegates (see CompanyAdminLinkCreateAPI, which is owner-only).
    """
    if not company:
        return False
    if company.company_user_id == user_id:
        return True
    return CompanyAdminLink.objects.filter(
        company=company, user_id=user_id, status=CompanyAdminLink.Status.ACCEPTED
    ).exists()


class CompanyAdminLinkCreateAPI(APIView):
    """Owner-only: invite a second user to delegate approval authority to."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Invite a delegate for company approval authority (owner only). The invitee must accept before it takes effect.",
    )
    def post(self, request):
        from db.user import User
        from utils.utils import DateTimeUtils
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()
        if not company:
            return CustomResponse(general_message="Verified company profile not found.").get_failure_response(status_code=403)

        muid = request.data.get('muid')
        delegate = User.objects.filter(muid=muid).first() if muid else None
        if not delegate:
            return CustomResponse(general_message="Delegate user not found.").get_failure_response(status_code=404)

        if delegate.id == user_id:
            return CustomResponse(general_message="You are already the owner.").get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        link = CompanyAdminLink.objects.filter(company=company, user=delegate).first()
        if link and link.status == CompanyAdminLink.Status.ACCEPTED:
            return CustomResponse(general_message="This user is already an accepted delegate.").get_failure_response()

        if link:
            link.status = CompanyAdminLink.Status.PENDING
            link.invited_by_id = user_id
            link.invited_at = now
            link.responded_at = None
            link.revoked_by = None
            link.revoked_at = None
            link.updated_by_id = user_id
            link.save(update_fields=[
                "status", "invited_by_id", "invited_at", "responded_at",
                "revoked_by", "revoked_at", "updated_by_id",
            ])
        else:
            CompanyAdminLink.objects.create(
                company=company, user=delegate,
                status=CompanyAdminLink.Status.PENDING,
                invited_by_id=user_id, invited_at=now,
                created_by_id=user_id, updated_by_id=user_id,
            )

        try:
            from api.notification.notifications_utils import NotificationUtils
            actor = User.every.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=delegate,
                title="Company Delegate Invitation",
                description=f"{actor.full_name} has invited you to be an approval delegate for {company.name}.",
                button="Respond", url=None, created_by=actor,
            )
        except Exception:
            pass

        return CustomResponse(general_message="Delegate invited successfully. Awaiting their acceptance.").get_success_response()


class CompanyAdminLinkAcceptAPI(APIView):
    """The invited delegate accepts or declines their invitation."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Accept or decline a company delegate invitation.",
    )
    def post(self, request, link_id):
        from utils.utils import DateTimeUtils
        user_id = JWTUtils.fetch_user_id(request)
        accept = bool(request.data.get('accept', True))

        link = CompanyAdminLink.objects.filter(id=link_id, user_id=user_id, status=CompanyAdminLink.Status.PENDING).first()
        if not link:
            return CustomResponse(general_message="Pending invitation not found.").get_failure_response(status_code=404)

        link.status = CompanyAdminLink.Status.ACCEPTED if accept else CompanyAdminLink.Status.DECLINED
        link.responded_at = DateTimeUtils.get_current_utc_time()
        link.updated_by_id = user_id
        link.save(update_fields=["status", "responded_at", "updated_by_id"])

        return CustomResponse(
            general_message=f"Invitation {'accepted' if accept else 'declined'} successfully."
        ).get_success_response()


class CompanyAdminLinkRevokeAPI(APIView):
    """Owner-only: revoke a delegate's approval authority."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Revoke a delegate's company approval authority (owner only).",
    )
    def delete(self, request, link_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()
        if not company:
            return CustomResponse(general_message="Verified company profile not found.").get_failure_response(status_code=403)

        link = CompanyAdminLink.objects.filter(
            id=link_id, company=company, status=CompanyAdminLink.Status.ACCEPTED
        ).first()
        if not link:
            return CustomResponse(general_message="Accepted delegate link not found.").get_failure_response(status_code=404)

        from utils.utils import DateTimeUtils
        link.status = CompanyAdminLink.Status.REVOKED
        link.revoked_by_id = user_id
        link.revoked_at = DateTimeUtils.get_current_utc_time()
        link.updated_by_id = user_id
        link.save(update_fields=["status", "revoked_by_id", "revoked_at", "updated_by_id"])

        return CustomResponse(general_message="Delegate revoked successfully.").get_success_response()


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
            "Nomination IS approval — there is no separate pending step; the "
            "mentor tier is granted immediately. Admin receives a passive "
            "notification and audit-log entry, but has no approval authority "
            "over this tier."
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

        application = serializer.save()

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            from django.conf import settings
            from api.dashboard.mentor.dash_mentor_helper import notify_admins_company_mentor_decision

            nominator = User.every.filter(id=user_id).first()

            # Notify the nominated user
            NotificationUtils.insert_notification(
                user=application.user,
                title=f"Company Mentor Approved: {company.name}"[:50],
                description=(
                    f"You have been approved as a Company Mentor for {company.name}."
                )[:200],
                button='View',
                url='/mentor/status/',
                created_by=nominator,
            )

            # Passive admin visibility + audit log — admin has no approval
            # authority over this decision (§4.5).
            notify_admins_company_mentor_decision(nominator, application, "approved (via nomination)")
        except Exception:
            pass

        return CustomResponse(
            general_message="User approved as Company Mentor successfully.",
            response=serializers.CompanyMentorListSerializer(application).data,
        ).get_success_response()


class CompanyMentorApplyAPI(APIView):
    """
    Self-onboarding: any authenticated user applies to become a specific
    company's mentor. Sits PENDING until the company owner reviews it via
    MentorVerifyAPI (owner is the sole verifier for this tier, per §4.2/§4.5).
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Company Mentor"],
        description="Apply to become a mentor for a specific company. Pending until the company owner reviews it.",
        request=serializers.CompanyMentorApplySerializer,
        responses={200: serializers.CompanyMentorListSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = serializers.CompanyMentorApplySerializer(
            data=request.data, context={"user_id": user_id},
        )
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        application = serializer.save()
        return CustomResponse(
            general_message="Application submitted successfully. It is pending review by the company owner.",
            response=serializers.CompanyMentorListSerializer(application).data,
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

        from db.user import UserMentor, MentorApplication
        applications = MentorApplication.objects.filter(
            tier=UserMentor.MentorTier.COMPANY_MENTOR,
            org=org,
        ).select_related("user").order_by("-created_at")

        serializer = serializers.CompanyMentorListSerializer(applications, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
