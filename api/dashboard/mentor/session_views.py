from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, JWTUtils, role_required, mentor_active_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.mentor import MentorshipSession
from db.task import UserIgLink
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers

class MentorSessionCreateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session'],
        description=(
            "Create a new mentorship session. "
            "For IG mentors, provide an 'ig' field. "
            "For company mentors, entity_id and session_type are auto-resolved from the mentor's company org. "
            "To create a recurring session, set is_recurring=true, recurrence_type ('DAILY', 'WEEKLY', 'MONTHLY'), "
            "recurrence_interval, and recurrence_end_date. This returns the parent session while auto-spawning children."
        ),
        request=serializers.SessionCreateSerializer,
        responses={200: serializers.SessionCreateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    @mentor_active_required
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        data = request.data.copy()
        serializer = serializers.SessionCreateSerializer(
            data=data, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            message = "Session created successfully."
            if serializer.data.get("recurrence_truncated"):
                message += (
                    " Note: the recurrence series was capped at 50 occurrences — "
                    "not all sessions through your requested end date were created."
                )
            return CustomResponse(
                general_message=message,
                response=serializer.data
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class MentorSessionListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session'],
        description="List all sessions created by the logged-in mentor, or get details of a specific session.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: serializers.SessionListSerializer(many=True)},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request, session_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        
        if session_id:
            session = MentorshipSession.objects.filter(id=session_id, created_by_id=user_id, is_deleted=False).first()
            if not session:
                return CustomResponse(general_message="Session not found.").get_failure_response(status_code=404)
            serializer = serializers.SessionDetailSerializer(session)
            return CustomResponse(response=serializer.data).get_success_response()
            
        sessions = MentorshipSession.objects.filter(created_by_id=user_id, is_deleted=False)
        
        status = request.query_params.get("status")
        if status:
            sessions = sessions.filter(status=status)
            
        paginated_queryset = CommonUtils.get_paginated_queryset(
            sessions, request, 
            search_fields=["title", "description"],
            sort_fields={"created_at": "created_at", "starts_at": "starts_at"}
        )
        
        page = list(paginated_queryset.get("queryset"))
        ig_map, org_map = serializers.SessionListSerializer.build_entity_maps(page)
        serializer = serializers.SessionListSerializer(page, many=True, context={"ig_map": ig_map, "org_map": org_map})
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class MentorSessionUpdateAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session'],
        description=(
            "Update or cancel a mentorship session. "
            "For a recurring session, pass apply_to_series=true to also apply the same "
            "logistics fields (title, description, mode, venue, meeting_link, max_participants — "
            "not starts_at/ends_at, which are per-occurrence) to every other still-SCHEDULED "
            "session in the series. Without it, only this occurrence is changed and the rest "
            "of the series is left untouched."
        ),
        request=serializers.SessionUpdateSerializer,
        responses={200: serializers.SessionUpdateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    @mentor_active_required
    def patch(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)

        session = MentorshipSession.objects.filter(id=session_id, created_by_id=user_id, is_deleted=False).first()

        if not session:
            return CustomResponse(
                general_message="Session not found."
            ).get_failure_response(status_code=404)

        if session.status in [MentorshipSession.Status.COMPLETED, MentorshipSession.Status.CANCELLED, MentorshipSession.Status.REJECTED]:
            return CustomResponse(
                general_message=f"Cannot edit a session that is {session.status.lower()}."
            ).get_failure_response()

        data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
        apply_to_series = bool(data.pop('apply_to_series', False))

        serializer = serializers.SessionUpdateSerializer(
            session, data=data, partial=True, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            series_updated = 0
            if apply_to_series and session.is_recurring:
                # Only logistics fields make sense across a whole series —
                # starts_at/ends_at are per-occurrence and must stay untouched.
                propagate_fields = {"title", "description", "mode", "venue", "meeting_link", "max_participants"}
                propagate_data = {k: v for k, v in serializer.validated_data.items() if k in propagate_fields}
                if propagate_data:
                    from utils.utils import DateTimeUtils
                    root_id = session.parent_session_id or session.id
                    propagate_data["updated_by_id"] = user_id
                    # .update() bypasses auto_now — set it explicitly.
                    propagate_data["updated_at"] = DateTimeUtils.get_current_utc_time()
                    series_updated = MentorshipSession.objects.filter(
                        Q(id=root_id) | Q(parent_session_id=root_id),
                        status=MentorshipSession.Status.SCHEDULED,
                        is_deleted=False,
                    ).exclude(id=session.id).update(**propagate_data)

            message = "Session updated successfully."
            if apply_to_series and session.is_recurring:
                message = f"Session updated successfully. Propagated to {series_updated} other session(s) in the series."

            return CustomResponse(
                general_message=message,
                response=serializer.data
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Mentor Session'],
        description="Delete a mentorship session.",
    )
    @role_required([RoleType.MENTOR.value])
    @mentor_active_required
    def delete(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)

        session = MentorshipSession.objects.filter(id=session_id, created_by_id=user_id, is_deleted=False).first()
        
        if not session:
            return CustomResponse(
                general_message="Session not found."
            ).get_failure_response(status_code=404)
            
        session.is_deleted = True
        session.save()
        return CustomResponse(
            general_message="Session deleted successfully."
        ).get_success_response()


class MentorSessionCompleteAPI(APIView):
    """
    POST /session/complete/<session_id>/ — the mentor manually marks a
    SCHEDULED session they created as COMPLETED, without waiting for the
    periodic transition_mentorship_session_statuses cron. Also records the
    session's duration as the mentor's contributed_minutes on their MENTOR
    participant link, and marks that link ATTENDED.
    """
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session'],
        description="Mark a scheduled mentorship session as completed.",
    )
    @role_required([RoleType.MENTOR.value])
    @mentor_active_required
    def post(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)

        session = MentorshipSession.objects.filter(
            id=session_id, created_by_id=user_id, is_deleted=False
        ).first()
        if not session:
            return CustomResponse(
                general_message="Session not found."
            ).get_failure_response(status_code=404)

        if session.status != MentorshipSession.Status.SCHEDULED:
            return CustomResponse(
                general_message=f"Only a scheduled session can be marked completed (current status: {session.status})."
            ).get_failure_response()

        from db.mentor import MentorshipSessionUserLink
        from utils.utils import DateTimeUtils

        now = DateTimeUtils.get_current_utc_time()
        session.status = MentorshipSession.Status.COMPLETED
        session.updated_by_id = user_id
        session.save(update_fields=["status", "updated_by_id", "updated_at"])

        duration_minutes = int((session.ends_at - session.starts_at).total_seconds() // 60)
        MentorshipSessionUserLink.objects.filter(
            session=session,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).update(
            attendance_status=MentorshipSessionUserLink.AttendanceStatus.ATTENDED,
            contributed_minutes=duration_minutes,
        )

        return CustomResponse(
            general_message="Session marked as completed."
        ).get_success_response()


class AdminSessionListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session'],
        description="Admin view to list all mentorship sessions.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("ig_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: serializers.SessionListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        sessions = MentorshipSession.objects.filter(is_deleted=False)
        
        status = request.query_params.get("status")
        ig_id = request.query_params.get("ig_id")
        
        if status:
            sessions = sessions.filter(status=status)
        if ig_id:
            sessions = sessions.filter(entity_id=ig_id, session_type=MentorshipSession.SessionType.IG_SESSION)
            
        paginated_queryset = CommonUtils.get_paginated_queryset(
            sessions, request, 
            search_fields=["title", "created_by__full_name"],
            sort_fields={"starts_at": "starts_at", "created_at": "created_at", "status": "status"}
        )
        
        page = list(paginated_queryset.get("queryset"))
        ig_map, org_map = serializers.SessionListSerializer.build_entity_maps(page)
        serializer = serializers.SessionListSerializer(page, many=True, context={"ig_map": ig_map, "org_map": org_map})
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class AdminSessionVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session'],
        description="Verify or reject a mentorship session.",
        request=serializers.AdminSessionVerifySerializer,
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)
        session = MentorshipSession.objects.filter(id=session_id, is_deleted=False).first()
        
        if not session:
            return CustomResponse(
                general_message="Session not found."
            ).get_failure_response(status_code=404)
            
        # Allowed admin transitions:
        #   PENDING_APPROVAL → SCHEDULED / REJECTED   (legacy pre-moderation)
        #   SCHEDULED        → CANCELLED              (reactive unpublish)
        target = request.data.get("status")
        allowed_transition = (
            (
                session.status == MentorshipSession.Status.PENDING_APPROVAL
                and target in [
                    MentorshipSession.Status.SCHEDULED,
                    MentorshipSession.Status.REJECTED,
                ]
            )
            or (
                session.status == MentorshipSession.Status.SCHEDULED
                and target == MentorshipSession.Status.CANCELLED
            )
        )
        if not allowed_transition:
            return CustomResponse(
                general_message="Invalid status transition for this session."
            ).get_failure_response(status_code=400)

        serializer = serializers.AdminSessionVerifySerializer(
            session, data=request.data, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            instance = serializer.save()
            status = serializer.validated_data.get('status')
            apply_to_series = serializer.validated_data.get('apply_to_series', False)
            
            message = f"Session status updated to {status} successfully."
            if apply_to_series and instance.is_recurring:
                message = f"Session and its pending series chain updated to {status} successfully."
                
            return CustomResponse(
                general_message=message
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class AvailableSessionListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Learner Session'],
        description=(
            "List all scheduled sessions available to the user — "
            "includes IG sessions for their groups and company sessions for linked company orgs."
        ),
        responses={200: serializers.SessionListSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        from django.db.models import Q
        from db.task import UserIgLink
        from db.organization import UserOrganizationLink

        # IGs the user belongs to
        user_ig_ids = UserIgLink.objects.filter(
            user_id=user_id
        ).values_list('ig_id', flat=True)

        # Campus orgs the user is linked to
        campus_org_ids = UserOrganizationLink.objects.filter(
            user_id=user_id,
            org__org_type='College',
        ).values_list('org_id', flat=True)

        sessions = MentorshipSession.objects.filter(
            Q(
                # IG sessions for the user's groups
                entity_id__in=user_ig_ids,
                session_type=MentorshipSession.SessionType.IG_SESSION,
            ) | Q(
                # Campus sessions for the user's college
                entity_id__in=campus_org_ids,
                session_type=MentorshipSession.SessionType.CAMPUS_SESSION,
            ) | Q(
                # All company sessions are available to every authenticated user
                session_type=MentorshipSession.SessionType.COMPANY_SESSION,
            ),
            status=MentorshipSession.Status.SCHEDULED,
            is_deleted=False,
        ).distinct()

        paginated_queryset = CommonUtils.get_paginated_queryset(
            sessions, request,
            search_fields=["title", "description"],
            sort_fields={"created_at": "created_at", "starts_at": "starts_at"}
        )

        page = list(paginated_queryset.get("queryset"))
        ig_map, org_map = serializers.SessionListSerializer.build_entity_maps(page)
        serializer = serializers.SessionListSerializer(page, many=True, context={"ig_map": ig_map, "org_map": org_map})
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()
