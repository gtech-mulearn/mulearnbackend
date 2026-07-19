from rest_framework.views import APIView
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.mentor import MentorshipSession, MentorshipSessionUserLink
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers

class SessionJoinAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session Participant'],
        description="Allows a MuLearn user to join a scheduled mentorship session.",
        request=serializers.ParticipantJoinSerializer,
        responses={200: serializers.ParticipantListSerializer},
    )
    def post(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        serializer = serializers.ParticipantJoinSerializer(
            data=request.data, context={"user_id": user_id, "session_id": session_id}
        )

        if serializer.is_valid():
            link = serializer.save()
            return CustomResponse(
                general_message="Successfully joined the session.",
                response=serializers.ParticipantListSerializer(link).data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()


class MentorAddParticipantAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session Participant'],
        description="Mentor view to manually add a participant to a specific session using muid.",
        request=serializers.MentorAddParticipantSerializer,
        responses={200: serializers.ParticipantListSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        serializer = serializers.MentorAddParticipantSerializer(
            data=request.data, context={"user_id": user_id, "session_id": session_id}
        )
        
        if serializer.is_valid():
            link = serializer.save()
            return CustomResponse(
                general_message="Successfully added participant to the session.",
                response=serializers.ParticipantListSerializer(link).data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()



class UserSessionHistoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session Participant'],
        description="List all mentorship sessions the logged-in user has joined.",
        responses={200: serializers.ParticipantListSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        links = MentorshipSessionUserLink.objects.filter(user_id=user_id).select_related('session', 'user')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            links, request,
            search_fields=["session__title", "participant_role"],
            sort_fields={"created_at": "created_at"}
        )

        page = list(paginated_queryset.get("queryset"))
        ig_map = serializers.ParticipantListSerializer.build_ig_map(page)
        serializer = serializers.ParticipantListSerializer(
            page, many=True, context={"ig_map": ig_map}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class MentorParticipantListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session Participant'],
        description="Mentor view to list all participants in a specific session.",
        responses={200: serializers.ParticipantListSerializer(many=True)},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        # Verify the logged-in mentor created this session
        if not MentorshipSession.objects.filter(id=session_id, created_by_id=user_id).exists():
            return CustomResponse(
                general_message="You don't have permission to view participants for this session."
            ).get_failure_response(status_code=403)
            
        links = MentorshipSessionUserLink.objects.filter(session_id=session_id).select_related('user', 'session')
        
        paginated_queryset = CommonUtils.get_paginated_queryset(
            links, request,
            search_fields=["user__full_name", "user__muid"],
            sort_fields={"created_at": "created_at", "user_full_name": "user__full_name"}
        )

        page = list(paginated_queryset.get("queryset"))
        ig_map = serializers.ParticipantListSerializer.build_ig_map(page)
        serializer = serializers.ParticipantListSerializer(
            page, many=True, context={"ig_map": ig_map}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class MentorParticipantUpdateAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session Participant'],
        description="Mentor view to update participant's attendance and progress.",
        request=serializers.ParticipantUpdateSerializer,
        responses={200: serializers.ParticipantUpdateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def patch(self, request, link_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        link = MentorshipSessionUserLink.objects.filter(id=link_id).select_related('session').first()
        if not link:
            return CustomResponse(
                general_message="Participant record not found."
            ).get_failure_response(status_code=404)
            
        # Verify the logged-in mentor created this session
        if link.session.created_by_id != user_id:
            return CustomResponse(
                general_message="You don't have permission to update participants for this session."
            ).get_failure_response(status_code=403)
            
        serializer = serializers.ParticipantUpdateSerializer(
            link, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Participant record updated successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class ParticipantFeedbackAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Session Participant'],
        description="Allows a user to submit feedback for a session they attended.",
        request=serializers.ParticipantFeedbackSerializer,
        responses={200: serializers.ParticipantListSerializer},
    )
    def patch(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)
        
        link = MentorshipSessionUserLink.objects.filter(session_id=session_id, user_id=user_id).first()
        if not link:
            return CustomResponse(
                general_message="You are not a participant of this session."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.ParticipantFeedbackSerializer(
            link, data=request.data, partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Feedback submitted successfully.",
                response=serializers.ParticipantListSerializer(link).data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()
