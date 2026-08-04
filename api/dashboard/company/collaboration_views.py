from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils
from db.company import Company, Collaboration
from .company_views import is_company_owner_or_admin

# PRD §15 — rate/abuse limit: cap how many open/pending collaboration posts
# a company can have live at once, mirroring job_views.MAX_PENDING_JOBS_PER_MENTOR.
MAX_ACTIVE_COLLABORATIONS_PER_COMPANY = 5


def _resolve_owner_or_admin_company(user_id):
    """Verified Company where `user_id` is the owner or an accepted co-admin delegate."""
    from db.company import CompanyAdminLink
    company = Company.objects.filter(company_user_id=user_id, status="verified").first()
    if company:
        return company
    return Company.objects.filter(
        admin_links__user_id=user_id,
        admin_links__status=CompanyAdminLink.Status.ACCEPTED,
        status="verified",
    ).first()


def _can_respond_as_target(user_id, roles, target_type, target_org_id):
    """
    True if `user_id` is the lead of the named campus/IG, mirroring the
    equivalent checks in api/dashboard/events/manage_views.py's
    `_caller_can_respond` for COLLAB_CAMPUS/COLLAB_IG.
    """
    if not target_type or not target_org_id:
        return False
    if target_type == Collaboration.TargetType.CAMPUS:
        from db.organization import UserOrganizationLink
        return (
            RoleType.CAMPUS_LEAD.value in roles
            and UserOrganizationLink.objects.filter(
                user_id=user_id, org_id=target_org_id, verified=True
            ).exists()
        )
    if target_type == Collaboration.TargetType.IG:
        # Use the same role-title convention as manage_views._caller_can_respond
        # and mentor_views._is_ig_lead_of (f'{ig.code} IGLead' in roles),
        # rather than a second, divergent UserIgLink-based lead check.
        from db.task import InterestGroup
        ig = InterestGroup.objects.filter(id=target_org_id).first()
        return bool(ig) and RoleType.IG_LEAD_ROLE(ig.code) in roles
    return False


class CompanyCollaborationListCreateAPI(APIView):
    """PRD §10.3 — a company posts a collaboration intent (open discovery or a direct invite)."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="List the authenticated company's own collaboration posts (any status).",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _resolve_owner_or_admin_company(user_id)
        if not company:
            return CustomResponse(general_message="Verified company profile not found.").get_failure_response(status_code=403)

        collaborations = Collaboration.objects.filter(company=company).order_by("-created_at")
        paginated = CommonUtils.get_paginated_queryset(
            collaborations, request,
            search_fields=["title", "description"],
            sort_fields={"created_at": "created_at", "status": "status"},
        )
        from .collaboration_serializers import CollaborationSerializer
        serializer = CollaborationSerializer(paginated.get("queryset"), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated.get("pagination")}
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Company'],
        description=(
            "Post a collaboration intent for your company (owner or accepted co-admin only). "
            "Omit target_type/target_org_id for an open discovery post visible to eligible "
            "campuses/IGs; supply both to directly invite a specific one."
        ),
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        company = _resolve_owner_or_admin_company(user_id)
        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(general_message="You must be the company owner or an accepted co-admin.").get_failure_response(status_code=403)

        active_count = Collaboration.objects.filter(
            company=company, status__in=[Collaboration.Status.OPEN, Collaboration.Status.PENDING],
        ).count()
        if active_count >= MAX_ACTIVE_COLLABORATIONS_PER_COMPANY:
            return CustomResponse(
                general_message=f"You already have {MAX_ACTIVE_COLLABORATIONS_PER_COMPANY} open/pending collaboration posts. Resolve those before posting more."
            ).get_failure_response(status_code=429)

        collab_type = request.data.get("collab_type")
        title = request.data.get("title")
        if collab_type not in Collaboration.CollabType.values:
            return CustomResponse(general_message="Invalid collab_type.").get_failure_response()
        if not title:
            return CustomResponse(general_message="title is required.").get_failure_response()

        target_type = request.data.get("target_type")
        target_org_id = request.data.get("target_org_id")
        if target_type and target_type not in Collaboration.TargetType.values:
            return CustomResponse(general_message="Invalid target_type.").get_failure_response()

        event_id = request.data.get("event_id")
        event = None
        if event_id:
            from db.events import Event
            event = Event.objects.filter(id=event_id).first()
            if not event or event.organiser_org_id != company.org_id:
                return CustomResponse(general_message="Event not found for this company.").get_failure_response(status_code=404)

        status = Collaboration.Status.PENDING if (target_type and target_org_id) else Collaboration.Status.OPEN

        collaboration = Collaboration.objects.create(
            company=company,
            collab_type=collab_type,
            title=title,
            description=request.data.get("description"),
            target_type=target_type or None,
            target_org_id=target_org_id or None,
            event=event,
            status=status,
            created_by_id=user_id,
            updated_by_id=user_id,
        )

        try:
            if status == Collaboration.Status.PENDING:
                from api.notification.notifications_utils import NotificationUtils
                from db.user import User
                actor = User.every.filter(id=user_id).first()
                lead_ids = _get_target_leads(target_type, target_org_id)
                for lead in User.objects.filter(id__in=lead_ids):
                    NotificationUtils.insert_notification(
                        user=lead,
                        title="New Collaboration Proposal",
                        description=f"{company.name} has proposed a collaboration: {title}.",
                        button="View", url=None, created_by=actor,
                    )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify target leads of collaboration proposal")

        return CustomResponse(
            general_message="Collaboration posted successfully.",
            response={"id": str(collaboration.id), "status": collaboration.status},
        ).get_success_response()


def _get_target_leads(target_type, target_org_id):
    """User ids of the current lead(s) of a specific campus/IG, for notification fan-out."""
    if target_type == Collaboration.TargetType.CAMPUS:
        from db.organization import UserOrganizationLink
        from db.user import UserRoleLink
        campus_users = UserOrganizationLink.objects.filter(
            org_id=target_org_id, verified=True
        ).values_list("user_id", flat=True)
        return list(UserRoleLink.objects.filter(
            user_id__in=campus_users, role__title=RoleType.CAMPUS_LEAD.value,
        ).values_list("user_id", flat=True))
    if target_type == Collaboration.TargetType.IG:
        from db.task import UserIgLink
        return list(UserIgLink.objects.filter(
            ig_id=target_org_id, assignment_type=UserIgLink.AssignmentType.LEAD, is_active=True,
        ).values_list("user_id", flat=True))
    return []


class CompanyCollaborationDiscoverAPI(APIView):
    """Public discovery feed of OPEN collaboration posts, for campuses/IGs to browse."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Browse open (undirected) collaboration posts from companies.",
        parameters=[
            OpenApiParameter("collab_type", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
    )
    def get(self, request):
        collaborations = Collaboration.objects.filter(status=Collaboration.Status.OPEN).select_related("company").order_by("-created_at")
        collab_type = request.query_params.get("collab_type")
        if collab_type:
            collaborations = collaborations.filter(collab_type=collab_type)

        paginated = CommonUtils.get_paginated_queryset(
            collaborations, request,
            search_fields=["title", "description", "company__name"],
            sort_fields={"created_at": "created_at"},
        )
        from .collaboration_serializers import CollaborationSerializer
        serializer = CollaborationSerializer(paginated.get("queryset"), many=True)
        return CustomResponse(
            response={"data": serializer.data, "pagination": paginated.get("pagination")}
        ).get_success_response()


class CompanyCollaborationRespondAPI(APIView):
    """A campus/IG lead responds to a collaboration — accept/decline a direct invite, or claim an open post."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description=(
            "Respond to a collaboration as a campus/IG lead. For a directly-invited (PENDING) "
            "collaboration, supply {\"accept\": true|false}. For an OPEN discovery post, supply "
            "{\"accept\": true, \"target_type\": ..., \"target_org_id\": ...} to claim it on "
            "behalf of your campus/IG."
        ),
    )
    def post(self, request, collaboration_id):
        from django.db import transaction

        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        with transaction.atomic():
            collaboration = Collaboration.objects.select_for_update().filter(id=collaboration_id).first()
            if not collaboration:
                return CustomResponse(general_message="Collaboration not found.").get_failure_response(status_code=404)

            if collaboration.status == Collaboration.Status.OPEN:
                target_type = request.data.get("target_type")
                target_org_id = request.data.get("target_org_id")
            elif collaboration.status == Collaboration.Status.PENDING:
                target_type, target_org_id = collaboration.target_type, collaboration.target_org_id
            else:
                return CustomResponse(general_message="This collaboration is no longer open for a response.").get_failure_response()

            if not _can_respond_as_target(user_id, roles, target_type, target_org_id):
                return CustomResponse(general_message="You are not authorized to respond on behalf of this campus/IG.").get_failure_response(status_code=403)

            accept = bool(request.data.get("accept", True))
            now = DateTimeUtils.get_current_utc_time()
            collaboration.target_type = target_type
            collaboration.target_org_id = target_org_id
            collaboration.responded_by_id = user_id
            collaboration.responded_at = now
            collaboration.updated_by_id = user_id

            if accept:
                collaboration.status = Collaboration.Status.ACCEPTED
            else:
                collaboration.status = Collaboration.Status.DECLINED
                collaboration.rejection_reason = request.data.get("rejection_reason")

            collaboration.save()

            connection_created = False
            if accept and collaboration.event_id:
                connection_created = _auto_wire_event_connection(collaboration, user_id)

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=collaboration.company.company_user,
                title=f"Collaboration {'Accepted' if accept else 'Declined'}",
                description=f'"{collaboration.title}" was {"accepted" if accept else "declined"}.',
                button="View", url=None, created_by=actor,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify company of collaboration response")

        return CustomResponse(
            general_message=f"Collaboration {'accepted' if accept else 'declined'} successfully.",
            response={"status": collaboration.status, "event_connection_created": connection_created},
        ).get_success_response()


def _auto_wire_event_connection(collaboration, actor_user_id):
    """
    PRD §10.3 — on acceptance, auto-create the matching EventConnection
    collaborator row so Collaboration never duplicates EventConnection's
    job; it only ever wires into it.
    """
    from db.events import EventConnection

    entity_type_map = {
        Collaboration.TargetType.CAMPUS: EventConnection.EntityType.COLLAB_CAMPUS,
        Collaboration.TargetType.IG: EventConnection.EntityType.COLLAB_IG,
    }
    entity_type = entity_type_map.get(collaboration.target_type)
    if not entity_type or not collaboration.target_org_id:
        return False

    _, created = EventConnection.objects.get_or_create(
        event=collaboration.event,
        entity_type=entity_type,
        entity_id=collaboration.target_org_id,
        defaults={
            "invite_status": EventConnection.InviteStatus.ACCEPTED,
            "role_label": collaboration.collab_type,
            "responded_at": DateTimeUtils.get_current_utc_time(),
            "created_by_id": actor_user_id,
            "updated_by_id": actor_user_id,
        },
    )
    return created


class CompanyCollaborationWithdrawAPI(APIView):
    """Owner-only: withdraw the company's own collaboration post before it's accepted/declined."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Withdraw a collaboration post (owner or accepted co-admin only).",
    )
    def delete(self, request, collaboration_id):
        user_id = JWTUtils.fetch_user_id(request)
        collaboration = Collaboration.objects.filter(id=collaboration_id).first()
        if not collaboration:
            return CustomResponse(general_message="Collaboration not found.").get_failure_response(status_code=404)

        if not is_company_owner_or_admin(user_id, collaboration.company):
            return CustomResponse(general_message="You are not authorized to withdraw this collaboration.").get_failure_response(status_code=403)

        if collaboration.status not in (Collaboration.Status.OPEN, Collaboration.Status.PENDING):
            return CustomResponse(general_message="Only an open or pending collaboration can be withdrawn.").get_failure_response()

        collaboration.status = Collaboration.Status.WITHDRAWN
        collaboration.updated_by_id = user_id
        collaboration.save(update_fields=["status", "updated_by_id", "updated_at"])
        return CustomResponse(general_message="Collaboration withdrawn successfully.").get_success_response()
