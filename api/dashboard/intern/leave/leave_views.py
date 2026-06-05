from django.utils.timezone import now
from datetime import timedelta
from rest_framework.views import APIView
from django.db.models import Sum
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternLeaveStatus
from utils.utils import CommonUtils
from db.intern import InternLeaveRequest

from .serializers import InternLeaveRequestSerializer, InternLeaveHistorySerializer

class InternLeaveRequestAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve intern leave request(s). Pass a leave_id to retrieve a specific request.",
        responses={200: InternLeaveHistorySerializer},
    )
    def get(self, request, leave_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if leave_id:
            leave = InternLeaveRequest.objects.filter(id=leave_id, user_id=user_id).first()
            if not leave:
                return CustomResponse(general_message="Leave request not found.").get_failure_response()
            serializer = InternLeaveHistorySerializer(leave)
            return CustomResponse(response=serializer.data).get_success_response()
            
        leaves = InternLeaveRequest.objects.filter(user_id=user_id).order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            leaves, request,
            ['leave_type', 'status'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = InternLeaveHistorySerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Submit a new intern leave request.",
        request=InternLeaveRequestSerializer,
        responses={200: OpenApiResponse(description="Leave request submitted successfully.")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = InternLeaveRequestSerializer(data=request.data, context={'user_id': user_id})
        
        if serializer.is_valid():
            serializer.save()
            
            from db.mentor import SystemActionLog
            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.INTERN_LEAVE_REQUEST.value,
                actor_user_id=user_id,
                subject_user_id=user_id,
                entity_name='intern_leave_request',
                entity_id=serializer.instance.id,
                new_data=serializer.data
            )
            
            return CustomResponse(general_message="Leave request submitted successfully.").get_success_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Cancel a pending intern leave request.",
        responses={200: OpenApiResponse(description="Leave request cancelled.")},
    )
    def patch(self, request, leave_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        leave = InternLeaveRequest.objects.filter(id=leave_id, user_id=user_id, status=InternLeaveStatus.PENDING.value).first()
        
        if not leave:
            return CustomResponse(general_message="Pending leave request not found.").get_failure_response()
            
        action = request.data.get("action")
        if action == "cancel":
            leave.status = InternLeaveStatus.CANCELLED.value
            leave.save()
            return CustomResponse(general_message="Leave request cancelled.").get_success_response()
            
        return CustomResponse(general_message="Invalid action.").get_failure_response()

class InternLeaveHistoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve paginated intern leave history.",
        responses={200: InternLeaveHistorySerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        leaves = InternLeaveRequest.objects.filter(user_id=user_id).order_by('-created_at')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            leaves, request,
            ['leave_type', 'status'],
            {'created_at': 'created_at', 'status': 'status'}
        )
        
        serializer = InternLeaveHistorySerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

class InternLeaveBalanceAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve the intern's leave balance (sick, casual, WFH, emergency).",
        responses={200: OpenApiResponse(description="Leave balance data by type.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        current_date = now().date()
        month_start = current_date.replace(day=1)
        
        iso_year, iso_week, weekday = current_date.isocalendar()
        week_start = current_date - timedelta(days=weekday - 1)
        
        approved_leaves = InternLeaveRequest.objects.filter(
            user_id=user_id,
            status=InternLeaveStatus.APPROVED.value
        )
        
        sick_used = approved_leaves.filter(
            leave_type='SICK',
            start_date__gte=month_start
        ).aggregate(Sum('duration_days'))['duration_days__sum'] or 0
        
        casual_used = approved_leaves.filter(
            leave_type='CASUAL',
            start_date__gte=month_start
        ).aggregate(Sum('duration_days'))['duration_days__sum'] or 0
        
        wfh_used = approved_leaves.filter(
            leave_type='WFH',
            start_date__gte=week_start
        ).aggregate(Sum('duration_days'))['duration_days__sum'] or 0
        
        data = {
            "SICK": {"limit": 2, "used": sick_used, "remaining": max(0, 2 - sick_used), "period": "month"},
            "CASUAL": {"limit": 1, "used": casual_used, "remaining": max(0, 1 - casual_used), "period": "month"},
            "WFH": {"limit": 2, "used": wfh_used, "remaining": max(0, 2 - wfh_used), "period": "week"},
            "EMERGENCY": {"limit": None, "used": approved_leaves.filter(leave_type='EMERGENCY').aggregate(Sum('duration_days'))['duration_days__sum'] or 0, "remaining": None, "period": "unlimited"}
        }
        
        return CustomResponse(response=data).get_success_response()
