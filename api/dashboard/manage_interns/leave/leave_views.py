from django.utils.timezone import now
from rest_framework.views import APIView
from django.db import transaction
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternLeaveStatus, InternGuildStatus
from utils.utils import CommonUtils
from db.intern import InternLeaveRequest, UserInternGuildLink

from .serializers import ManageInternLeaveSerializer

class ManageInternLeaveAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="List all intern leave requests, or retrieve a single leave request by ID.",
        responses={200: ManageInternLeaveSerializer},
    )
    def get(self, request, leave_id=None):
        if leave_id:
            leave = InternLeaveRequest.objects.filter(id=leave_id).first()
            if not leave:
                return CustomResponse(general_message="Leave request not found.").get_failure_response()
            serializer = ManageInternLeaveSerializer(leave)
            return CustomResponse(response=serializer.data).get_success_response()

        leaves = InternLeaveRequest.objects.select_related('user').all().order_by('-created_at')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            leaves, request,
            ['user__full_name', 'leave_type', 'status'],
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

    @role_required([RoleType.ADMIN.value, RoleType.INTERN.value, RoleType.INTERN_LEAD.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Review (approve/reject) an intern leave request.",
        responses={200: OpenApiResponse(description="Leave request reviewed successfully.")},
    )
    def patch(self, request, leave_id):
        admin_id = JWTUtils.fetch_user_id(request)
        action = request.data.get("action")
        review_note = request.data.get("review_note")
        
        if action not in ["approve", "reject"]:
            return CustomResponse(general_message="Invalid action. Must be 'approve' or 'reject'.").get_failure_response()
            
        leave = InternLeaveRequest.objects.filter(id=leave_id, status=InternLeaveStatus.PENDING.value).first()
        if not leave:
            return CustomResponse(general_message="Pending leave request not found.").get_failure_response()
            
        with transaction.atomic():
            if action == "approve":
                leave.status = InternLeaveStatus.APPROVED.value
                
                today = now().date()
                if leave.start_date <= today <= leave.end_date:
                    guild_link = UserInternGuildLink.objects.filter(user_id=leave.user_id).first()
                    if guild_link and guild_link.status != InternGuildStatus.ON_LEAVE.value:
                        guild_link.previous_status = guild_link.status
                        guild_link.status = InternGuildStatus.ON_LEAVE.value
                        guild_link.updated_by_id = admin_id
                        guild_link.save(update_fields=['status', 'previous_status', 'updated_by_id'])
                        
            elif action == "reject":
                leave.status = InternLeaveStatus.REJECTED.value
                
            leave.reviewed_by_id = admin_id
            leave.reviewed_at = now()
            leave.review_note = review_note
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
