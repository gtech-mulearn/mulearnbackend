from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from .company_views import is_company_owner_or_admin, _get_company_for_user


class IgSponsorshipRequestAPI(APIView):
    """PRD §7.3 — a company requests to be the recognised sponsor of an existing IG (owner/accepted co-admin only)."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Request sponsorship of an Interest Group on behalf of your company. Subject to platform-admin approval.",
    )
    def post(self, request, ig_id):
        from django.db import transaction
        from db.task import InterestGroup

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(general_message="You must be the company owner or an accepted co-admin.").get_failure_response(status_code=403)

        with transaction.atomic():
            ig = InterestGroup.objects.select_for_update().filter(id=ig_id).first()
            if not ig:
                return CustomResponse(general_message="Interest Group not found.").get_failure_response(status_code=404)

            if ig.sponsor_status == "approved" and ig.sponsor_company_id and ig.sponsor_company_id != company.id:
                return CustomResponse(general_message="This Interest Group is already sponsored by another company.").get_failure_response()

            # Block a second company's request while one is already pending
            # review — otherwise it silently overwrites the first company's
            # in-flight request (whoever an admin later approves "wins" a
            # request the requester never knew was contested).
            if ig.sponsor_status == "pending" and ig.sponsor_company_id and ig.sponsor_company_id != company.id:
                return CustomResponse(
                    general_message="This Interest Group already has a pending sponsorship request from another company."
                ).get_failure_response()

            ig.sponsor_company = company
            ig.sponsor_status = "pending"
            ig.updated_by_id = user_id
            ig.save(update_fields=["sponsor_company", "sponsor_status", "updated_by", "updated_at"])

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User, UserRoleLink
            actor = User.every.filter(id=user_id).first()
            for admin_link in UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related("user"):
                NotificationUtils.insert_notification(
                    user=admin_link.user,
                    title="New IG Sponsorship Request",
                    description=f"{company.name} has requested to sponsor the '{ig.name}' Interest Group.",
                    button="Review", url=None, created_by=actor,
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify admins of IG sponsorship request")

        return CustomResponse(general_message="Sponsorship request submitted. Awaiting admin approval.").get_success_response()


class IgSponsorshipReviewAPI(APIView):
    """Platform-admin approves/rejects a pending IG sponsorship request."""
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Approve or reject a pending IG sponsorship request (platform admin only).",
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, ig_id):
        from db.task import InterestGroup

        user_id = JWTUtils.fetch_user_id(request)
        ig = InterestGroup.objects.filter(id=ig_id, sponsor_status="pending").first()
        if not ig:
            return CustomResponse(general_message="No pending sponsorship request found for this Interest Group.").get_failure_response(status_code=404)

        approve = bool(request.data.get("approve", True))
        ig.sponsor_status = "approved" if approve else "rejected"
        if not approve:
            ig.sponsor_company = None
        ig.updated_by_id = user_id
        ig.save(update_fields=["sponsor_status", "sponsor_company", "updated_by", "updated_at"])

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User
            actor = User.every.filter(id=user_id).first()
            company = ig.sponsor_company if approve else None
            if company:
                NotificationUtils.insert_notification(
                    user=company.company_user,
                    title="IG Sponsorship Approved" if approve else "IG Sponsorship Rejected",
                    description=f"Your sponsorship request for '{ig.name}' was {'approved' if approve else 'rejected'}.",
                    button=None, url=None, created_by=actor,
                )
        except Exception:
            import logging
            logging.getLogger(__name__).exception("Failed to notify company of IG sponsorship decision")

        return CustomResponse(
            general_message=f"IG sponsorship {'approved' if approve else 'rejected'} successfully."
        ).get_success_response()


class IgSponsorshipMetricsAPI(APIView):
    """
    PRD §7.3 — IG health metrics visible to the sponsoring company
    (membership growth, activity level), restricted to the company that is
    the IG's current *approved* sponsor.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Company'],
        description="Health metrics (membership growth, activity level) for an Interest Group your company sponsors.",
    )
    def get(self, request, ig_id):
        from django.utils import timezone
        from datetime import timedelta
        from db.task import InterestGroup, UserIgLink, TaskList, KarmaActivityLog
        from db.mentor import MentorshipSession

        user_id = JWTUtils.fetch_user_id(request)
        company = _get_company_for_user(user_id)
        if not company or not is_company_owner_or_admin(user_id, company):
            return CustomResponse(general_message="You must be the company owner or an accepted co-admin.").get_failure_response(status_code=403)

        ig = InterestGroup.objects.filter(
            id=ig_id, sponsor_status="approved", sponsor_company=company,
        ).first()
        if not ig:
            return CustomResponse(
                general_message="This Interest Group is not sponsored by your company."
            ).get_failure_response(status_code=404)

        thirty_days_ago = timezone.now() - timedelta(days=30)
        member_links = UserIgLink.objects.filter(
            ig=ig, assignment_type=UserIgLink.AssignmentType.LEARNER, is_active=True,
        )
        total_members = member_links.count()
        new_members_30d = member_links.filter(created_at__gte=thirty_days_ago).count()

        active_tasks = TaskList.objects.filter(ig=ig, active=True).count()
        completions_30d = KarmaActivityLog.objects.filter(
            task__ig=ig, created_at__gte=thirty_days_ago,
        ).count()
        sessions_30d = MentorshipSession.objects.filter(
            session_type=MentorshipSession.SessionType.IG_SESSION, entity_id=ig.id,
            starts_at__gte=thirty_days_ago,
        ).count()

        return CustomResponse(response={
            "ig_id": str(ig.id),
            "ig_name": ig.name,
            "membership": {
                "total_members": total_members,
                "new_members_last_30_days": new_members_30d,
            },
            "activity_level": {
                "active_tasks": active_tasks,
                "task_completions_last_30_days": completions_30d,
                "sessions_last_30_days": sessions_30d,
            },
        }).get_success_response()
