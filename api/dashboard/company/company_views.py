from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.company import Company, CompanyAdminLink
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers


# PRD §4.4.5 open question, resolved: a small cap keeps the co-admin access
# list auditable and bounds the abuse surface of a compromised owner account
# minting many delegates.
MAX_ACCEPTED_ADMIN_LINKS_PER_COMPANY = 5


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

        # PRD §4.4.5 — cap co-admins per company to keep the access list
        # auditable. Counts accepted + still-pending invites so the owner
        # can't queue past the cap either.
        active_link_count = CompanyAdminLink.objects.filter(
            company=company, status__in=[CompanyAdminLink.Status.ACCEPTED, CompanyAdminLink.Status.PENDING],
        ).exclude(user=delegate).count()
        if active_link_count >= MAX_ACCEPTED_ADMIN_LINKS_PER_COMPANY:
            return CustomResponse(
                general_message=f"You already have {MAX_ACCEPTED_ADMIN_LINKS_PER_COMPANY} accepted/pending delegates. Revoke one before inviting another."
            ).get_failure_response(status_code=429)

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
            import logging
            logging.getLogger(__name__).exception("Failed to notify delegate of company admin-link invitation")

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

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=link.user,
                title="Company Delegate Access Revoked",
                description=f"Your approval delegate access for {company.name} has been revoked.",
                button=None, url=None, created_by=actor,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify delegate of company admin-link revocation")

        return CustomResponse(general_message="Delegate revoked successfully.").get_success_response()


class CompanyAdminLinkListAPI(APIView):
    """Owner or accepted co-admin: view the full admin-link audit trail for the company."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="List the full history of co-admin invites/acceptances/revocations for the authenticated company (owner or accepted co-admin only).",
        responses={200: serializers.CompanyAdminLinkSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()
        if not company:
            company = Company.objects.filter(
                admin_links__user_id=user_id,
                admin_links__status=CompanyAdminLink.Status.ACCEPTED,
                status="verified",
            ).first()

        if not company:
            return CustomResponse(general_message="Verified company profile not found or access denied.").get_failure_response(status_code=403)

        links = CompanyAdminLink.objects.filter(company=company).select_related(
            "user", "invited_by", "revoked_by"
        ).order_by("-created_at")
        serializer = serializers.CompanyAdminLinkSerializer(links, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class CompanyAdminLinkLeaveAPI(APIView):
    """Self-removal: a co-admin voluntarily gives up their own delegate authority."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Voluntarily leave as a company delegate (self-removal, no owner action required).",
    )
    def delete(self, request, link_id):
        user_id = JWTUtils.fetch_user_id(request)

        link = CompanyAdminLink.objects.filter(
            id=link_id, user_id=user_id, status=CompanyAdminLink.Status.ACCEPTED
        ).first()
        if not link:
            return CustomResponse(general_message="Accepted delegate link not found.").get_failure_response(status_code=404)

        from utils.utils import DateTimeUtils
        link.status = CompanyAdminLink.Status.REVOKED
        link.revoked_by_id = user_id
        link.revoked_at = DateTimeUtils.get_current_utc_time()
        link.updated_by_id = user_id
        link.save(update_fields=["status", "revoked_by_id", "revoked_at", "updated_by_id"])

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=link.company.company_user,
                title="Company Delegate Left",
                description=f"{actor.full_name} has left as an approval delegate for {link.company.name}.",
                button=None, url=None, created_by=actor,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify owner of delegate self-removal")

        return CustomResponse(general_message="You have left as a company delegate successfully.").get_success_response()


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
        description="Update the profile of the authenticated company (creator only).",
        request=serializers.CompanyUpdateSerializer,
        responses={200: serializers.CompanyUpdateSerializer},
    )
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()
        
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


def _deactivate_company(company, actor_user_id):
    """
    PRD §4.2/§4.3 — soft-offboard a company: reuses the existing unused
    deleted_at/deleted_by columns and flips status to 'deactivated' so every
    existing status='verified' gate (public profile, job/task creation,
    mentor nomination, etc.) rejects it for free. Also revokes all ACCEPTED
    admin-links so a later reactivation doesn't silently resurrect stale
    co-admin authority.
    """
    from utils.utils import DateTimeUtils
    now = DateTimeUtils.get_current_utc_time()

    company.status = "deactivated"
    company.deleted_at = now
    company.deleted_by = actor_user_id
    company.updated_by = actor_user_id
    company.updated_at = now
    company.save(update_fields=["status", "deleted_at", "deleted_by", "updated_by", "updated_at"])

    revoked_links = list(CompanyAdminLink.objects.filter(company=company, status=CompanyAdminLink.Status.ACCEPTED))
    CompanyAdminLink.objects.filter(company=company, status=CompanyAdminLink.Status.ACCEPTED).update(
        status=CompanyAdminLink.Status.REVOKED, revoked_by_id=actor_user_id, revoked_at=now, updated_by_id=actor_user_id,
    )
    return revoked_links


class CompanyDeactivateAPI(APIView):
    """Owner-only self-service deactivation (PRD §4.4.4 — co-admins are explicitly excluded)."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Deactivate your own company (owner only). Co-admins cannot perform this action.",
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(company_user_id=user_id, status="verified").first()
        if not company:
            return CustomResponse(general_message="Verified company profile not found.").get_failure_response(status_code=403)

        revoked_links = _deactivate_company(company, user_id)

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            from api.dashboard.mentor.dash_mentor_helper import notify_admins_company_mentor_decision
            actor = User.every.filter(id=user_id).first()
            for link in revoked_links:
                NotificationUtils.insert_notification(
                    user=link.user,
                    title="Company Deactivated",
                    description=f"{company.name} has been deactivated; your co-admin access has been revoked.",
                    button=None, url=None, created_by=actor,
                )
            _notify_admins_company_action(actor, company, "deactivated (self-service by owner)")
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify on company self-deactivation")

        return CustomResponse(general_message="Company deactivated successfully.").get_success_response()


class CompanyAdminDeactivateAPI(APIView):
    """Platform-Admin-only offboarding of any company (fraud, policy violation, etc)."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Deactivate any company (platform admin only).",
    )
    @role_required([RoleType.ADMIN.value])
    def post(self, request, company_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(id=company_id, status="verified").first()
        if not company:
            return CustomResponse(general_message="Verified company not found.").get_failure_response(status_code=404)

        revoked_links = _deactivate_company(company, user_id)

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            from db.mentor import SystemActionLog
            actor = User.every.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=company.company_user,
                title="Company Deactivated by Admin",
                description=f"Your company {company.name} has been deactivated by a platform admin.",
                button=None, url=None, created_by=actor,
            )
            for link in revoked_links:
                NotificationUtils.insert_notification(
                    user=link.user,
                    title="Company Deactivated",
                    description=f"{company.name} has been deactivated; your co-admin access has been revoked.",
                    button=None, url=None, created_by=actor,
                )
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.COMPANY_DEACTIVATED,
                actor_user=actor,
                subject_user=company.company_user,
                entity_name='company',
                entity_id=company.id,
                old_data={'status': 'verified'},
                new_data={'status': 'deactivated'},
                remarks="deactivated by platform admin",
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify on admin-triggered company deactivation")

        return CustomResponse(general_message="Company deactivated successfully.").get_success_response()


class CompanyReactivateAPI(APIView):
    """Platform-Admin-only reactivation of a previously deactivated company."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Reactivate a previously-deactivated company, restoring verified status (platform admin only).",
    )
    @role_required([RoleType.ADMIN.value])
    def post(self, request, company_id):
        user_id = JWTUtils.fetch_user_id(request)
        company = Company.objects.filter(id=company_id, status="deactivated").first()
        if not company:
            return CustomResponse(general_message="Deactivated company not found.").get_failure_response(status_code=404)

        company.status = "verified"
        company.deleted_at = None
        company.deleted_by = None
        company.updated_by = user_id
        company.save(update_fields=["status", "deleted_at", "deleted_by", "updated_by", "updated_at"])

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=company.company_user,
                title="Company Reactivated",
                description=f"Your company {company.name} has been reactivated by a platform admin.",
                button=None, url=None, created_by=actor,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify on company reactivation")

        return CustomResponse(general_message="Company reactivated successfully.").get_success_response()


def _notify_admins_company_action(actor, company, action_description):
    """
    Passive admin audit visibility for owner-initiated company-level actions
    (e.g. self-deactivation), mirroring notify_admins_company_mentor_decision's
    shape (PRD §4.4.6/§15): admin gets a notification + SystemActionLog entry,
    with no approval authority over the action itself.
    """
    from api.notification.notifications_utils import NotificationUtils
    from db.user import UserRoleLink
    from db.mentor import SystemActionLog
    from django.conf import settings

    admin_links = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
    for admin_link in admin_links:
        NotificationUtils.insert_notification(
            user=admin_link.user,
            title="Company Self-Deactivated",
            description=f"{actor.full_name} (owner) has {action_description} for {company.name}. For your visibility — no action needed.",
            button="View",
            url=f"{settings.FR_DOMAIN_NAME}/dashboard/admin/companies/{company.id}/",
            created_by=actor,
        )

    SystemActionLog.objects.create(
        action_type=SystemActionLog.ActionType.COMPANY_DEACTIVATED,
        actor_user=actor,
        subject_user=company.company_user,
        entity_name='company',
        entity_id=company.id,
        old_data={'status': 'verified'},
        new_data={'status': 'deactivated'},
        remarks=action_description,
    )


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
            "deactivated_companies": companies.filter(status="deactivated").count(),
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
    def post(self, request):
        from api.dashboard.mentor.dash_mentor_helper import get_verified_company_for_mentor

        user_id = JWTUtils.fetch_user_id(request)
        company = get_verified_company_for_mentor(user_id)

        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(
                general_message="You must be the company owner or an accepted co-admin to nominate mentors."
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
    def get(self, request):
        from api.dashboard.mentor.dash_mentor_helper import get_verified_company_for_mentor

        user_id = JWTUtils.fetch_user_id(request)
        company = get_verified_company_for_mentor(user_id)

        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(
                general_message="You must be the company owner or an accepted co-admin to view mentor applications."
            ).get_failure_response(status_code=403)

        org = company.org

        if not org:
            return CustomResponse(
                general_message="Company organization record not found."
            ).get_failure_response(status_code=404)

        from db.user import MentorApplication
        applications = MentorApplication.objects.filter(
            mentor_tier=MentorApplication.MentorTier.COMPANY_MENTOR,
            org=org,
        ).select_related("user").order_by("-created_at")

        serializer = serializers.CompanyMentorListSerializer(applications, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
