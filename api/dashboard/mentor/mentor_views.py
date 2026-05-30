from rest_framework.views import APIView
from django.db.models import Q
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.user import UserMentor
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers

class MentorRegistrationAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Submit a new mentor registration.",
        request=serializers.MentorRegisterSerializer,
        responses={200: serializers.MentorRegisterSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        if UserMentor.objects.filter(user_id=user_id).exists():
            return CustomResponse(
                general_message="A mentor request already exists for your account."
            ).get_failure_response()

        serializer = serializers.MentorRegisterSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Mentor registration submitted successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Update a pending mentor application or resubmit a rejected one.",
        request=serializers.MentorUpdateSerializer,
        responses={200: serializers.MentorUpdateSerializer},
    )
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        mentor = UserMentor.objects.filter(user_id=user_id).first()

        if not mentor:
            return CustomResponse(
                general_message="No mentor registration request found for your account."
            ).get_failure_response(status_code=404)

        if mentor.status == UserMentor.Status.APPROVED:
            return CustomResponse(
                general_message="Your mentor application is already approved. Please use the profile endpoint to update your details."
            ).get_failure_response()

        serializer = serializers.MentorUpdateSerializer(
            mentor, data=request.data, partial=True, context={"user_id": user_id}
        )

        if serializer.is_valid():
            if mentor.status == UserMentor.Status.REJECTED:
                serializer.save(status=UserMentor.Status.PENDING, verification_note=None)
                msg = "Mentor registration updated and resubmitted successfully."
            else:
                serializer.save()
                msg = "Mentor application updated successfully."

            return CustomResponse(
                general_message=msg,
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class MentorStatusAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Check the status of a mentor registration.",
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        
        mentor = UserMentor.objects.filter(user_id=user_id).first()
        if not mentor:
            return CustomResponse(
                general_message="No mentor request found for your account."
            ).get_failure_response(status_code=404)
            
        return CustomResponse(
            response={
                "status": mentor.status,
                "verification_note": mentor.verification_note,
                "mentor_id": mentor.id,
            }
        ).get_success_response()

class MentorProfileAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Retrieve the profile of a verified mentor.",
        responses={200: serializers.MentorDetailSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorDetailSerializer(mentor)
        return CustomResponse(response=serializer.data).get_success_response()

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Update the profile of a verified mentor.",
        request=serializers.MentorUpdateSerializer,
        responses={200: serializers.MentorUpdateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        mentor = UserMentor.objects.filter(user_id=user_id, status=UserMentor.Status.APPROVED).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorUpdateSerializer(
            mentor, data=request.data, partial=True, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Mentor profile updated successfully.",
                response=serializers.MentorDetailSerializer(mentor).data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class MentorListAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="List all mentor applications with filtering.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("mentor_tier", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: serializers.MentorListSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        mentors = UserMentor.objects.all()

        status = request.query_params.get("status")
        mentor_tier = request.query_params.get("mentor_tier")

        if status:
            mentors = mentors.filter(status=status)
        if mentor_tier:
            mentors = mentors.filter(mentor_tier=mentor_tier)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            mentors, request, 
            search_fields=["user__full_name", "user__email"],
            sort_fields={"created_at": "created_at", "status": "status", "user_full_name": "user__full_name"}
        )
        
        serializer = serializers.MentorListSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

class MentorDetailAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Get details of a specific mentor by ID.",
        responses={200: serializers.MentorDetailSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request, mentor_id):
        mentor = UserMentor.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorDetailSerializer(mentor)
        return CustomResponse(response=serializer.data).get_success_response()

class MentorVerifyAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor'],
        description="Verify or reject a mentor application.",
        request=serializers.MentorVerifySerializer,
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, mentor_id):
        user_id = JWTUtils.fetch_user_id(request)
        mentor = UserMentor.objects.filter(id=mentor_id).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor request not found."
            ).get_failure_response(status_code=404)
            
        if mentor.status == UserMentor.Status.APPROVED:
            return CustomResponse(
                general_message="Mentor is already approved."
            ).get_failure_response()
            
        serializer = serializers.MentorVerifySerializer(
            mentor, data=request.data, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"Mentor status updated to {serializer.validated_data.get('status')} successfully."
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

class MentorPublicProfileAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Public'],
        description="View a mentor's profile publicly.",
        responses={200: serializers.MentorDetailSerializer},
    )
    def get(self, request, mentor_id):
        mentor = UserMentor.objects.filter(id=mentor_id, status=UserMentor.Status.APPROVED).first()
        
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found or not approved."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.MentorDetailSerializer(mentor)
        return CustomResponse(response=serializer.data).get_success_response()
