from django.utils.timezone import now
from rest_framework.views import APIView
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from utils.intern_permissions import (
    INACTIVE, ON_LEAVE, by_current_members, current_membership, include_former, is_admin, scope_records,
    self_review_error,
)
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternLeaveStatus
from utils.utils import CommonUtils, DateTimeUtils
from db.intern import InternLeaveRequest

from .serializers import ManageInternLeaveSerializer

# Plain interns use intern/leave/ for their own requests.
LEAVE_MANAGE_ROLES = [RoleType.ADMIN.value, RoleType.INTERN_LEAD.value]
REVIEW_NOTE_MAX_LENGTH = 300


def scoped_leave(request):
    """Leave the caller may manage: Admin all; Lead requests made in their team (former members included)."""
    return scope_records(InternLeaveRequest.objects.select_related('user', 'team', 'reviewed_by'), request)


class ManageInternLeaveAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(LEAVE_MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "List intern leave requests, or one by id. Admin: every team (optional `team_id`). "
            "Intern Lead: requests made in their team. The list shows by default only requests of "
            "people who are still current members of that team (INACTIVE included); "
            "`include_former=true` also returns those of people who have left, and, for Admins, "
            "requests from before teams. One request by id includes former members."
        ),
        parameters=[
            OpenApiParameter(name='team_id', description='Admin only: one team', required=False, type=str),
            OpenApiParameter(name='include_former', description='true: also people who left the team', required=False, type=str),
        ],
        responses={200: ManageInternLeaveSerializer},
    )
    def get(self, request, leave_id=None):
        if leave_id:
            leave = scoped_leave(request).filter(id=leave_id).first()
            if not leave:
                return CustomResponse(general_message="Leave request not found.").get_failure_response()
            serializer = ManageInternLeaveSerializer(leave)
            return CustomResponse(response=serializer.data).get_success_response()

        leaves = scoped_leave(request).order_by('-created_at')
        if not include_former(request):
            leaves = by_current_members(leaves)
        team_id = request.query_params.get('team_id')
        if team_id and is_admin(request):
            leaves = leaves.filter(team_id=team_id)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            leaves, request,
            ['user__full_name', 'user__muid', 'leave_type', 'status'],
            {'created_at': 'created_at', 'status': 'status'}
        )

        serializer = ManageInternLeaveSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()


class ManageInternLeaveReviewAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(LEAVE_MANAGE_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Approve or reject a pending leave request: `{\"action\": \"approve\" | \"reject\", "
            "\"review_note\": \"...\"}` (review_note optional, max 300). Admin: any request. Intern "
            "Lead: requests made in their team, not their own. Approving leave that covers today "
            "(IST) puts the intern's current membership ON_LEAVE; later starts are handled by the "
            "daily cron."
        ),
        responses={200: OpenApiResponse(description="Leave request reviewed successfully.")},
    )
    def patch(self, request, leave_id):
        admin_id = JWTUtils.fetch_user_id(request)
        action = request.data.get("action")
        review_note = request.data.get("review_note")

        if action not in ["approve", "reject"]:
            return CustomResponse(general_message="Invalid action. Must be 'approve' or 'reject'.").get_failure_response()
        if review_note is not None and not isinstance(review_note, str):
            return CustomResponse(general_message="review_note must be text.").get_failure_response()
        review_note = (review_note or "").strip() or None
        if review_note and len(review_note) > REVIEW_NOTE_MAX_LENGTH:
            return CustomResponse(
                general_message=f"review_note cannot exceed {REVIEW_NOTE_MAX_LENGTH} characters."
            ).get_failure_response()

        with transaction.atomic():
            leave = (
                scope_records(InternLeaveRequest.objects.select_for_update(), request)
                .filter(id=leave_id, status=InternLeaveStatus.PENDING.value).first()
            )
            if not leave:
                return CustomResponse(general_message="Pending leave request not found.").get_failure_response()
            own = self_review_error(request, leave.user_id, "leave request")
            if own:
                return CustomResponse(general_message=own).get_failure_response()

            if action == "approve":
                leave.status = InternLeaveStatus.APPROVED.value

                today = DateTimeUtils.get_ist_today()
                if leave.start_date <= today <= leave.end_date:
                    # The person's current row, wherever they are now (none if deactivated).
                    link = current_membership(leave.user_id, lock=True)
                    # Someone marked INACTIVE stays INACTIVE (the daily leave job skips them too).
                    if link and link.intern_status not in (ON_LEAVE, INACTIVE):
                        link.previous_intern_status = link.intern_status
                        link.intern_status = ON_LEAVE
                        link.updated_by_id = admin_id
                        link.save(update_fields=['intern_status', 'previous_intern_status', 'updated_by', 'updated_at'])

            elif action == "reject":
                leave.status = InternLeaveStatus.REJECTED.value

            leave.reviewed_by_id = admin_id
            leave.reviewed_at = now()
            leave.review_note = review_note
            leave.updated_by_id = admin_id
            leave.save()

            from db.mentor import SystemActionLog
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.INTERN_LEAVE_REVIEW.value,
                actor_user_id=admin_id,
                subject_user_id=leave.user_id,
                entity_name='intern_leave_request',
                entity_id=leave.id,
                new_data={"action": action, "review_note": review_note}
            )

        return CustomResponse(general_message=f"Leave request {action}ed successfully.").get_success_response()
