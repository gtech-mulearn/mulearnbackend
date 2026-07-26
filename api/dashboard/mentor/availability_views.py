from rest_framework.views import APIView
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.mentor import MentorAvailabilitySlot
from db.task import UserIgLink
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from . import serializers

class MentorAvailabilitySlotAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Availability'],
        description="List all availability slots for the logged-in mentor.",
        parameters=[
            OpenApiParameter("ig_id", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False),
            OpenApiParameter("is_active", OpenApiTypes.BOOL, OpenApiParameter.QUERY, required=False),
        ],
        responses={200: serializers.AvailabilitySlotSerializer(many=True)},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request, slot_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        
        if slot_id:
            slot = MentorAvailabilitySlot.objects.filter(id=slot_id, mentor_user_id=user_id).first()
            if not slot:
                return CustomResponse(
                    general_message="Availability slot not found."
                ).get_failure_response(status_code=404)
            return CustomResponse(response=serializers.AvailabilitySlotSerializer(slot).data).get_success_response()
            
        slots = MentorAvailabilitySlot.objects.filter(mentor_user_id=user_id)
        
        ig_id = request.query_params.get("ig_id")
        is_active = request.query_params.get("is_active")
        
        if ig_id:
            slots = slots.filter(ig_id=ig_id)
        if is_active is not None:
            slots = slots.filter(is_active=is_active.lower() == 'true')
            
        paginated_queryset = CommonUtils.get_paginated_queryset(
            slots, request, 
            search_fields=["ig__name"],
            sort_fields={"weekday": "weekday", "start_time": "start_time", "created_at": "created_at"}
        )
        
        serializer = serializers.AvailabilitySlotSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Mentor Availability'],
        description="Create a new mentor availability slot.",
        request=serializers.AvailabilitySlotCreateUpdateSerializer,
        responses={200: serializers.AvailabilitySlotCreateUpdateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        ig_id = request.data.get("ig")

        # Availability is a mentor-level setting. An IG is optional: when one is
        # supplied we verify the mentor is actually assigned to it, but a slot
        # with no IG (ig=NULL) is valid and applies across all the mentor's IGs.
        if ig_id and not UserIgLink.objects.filter(
            user_id=user_id,
            ig_id=ig_id,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True
        ).exists():
            return CustomResponse(
                general_message="You are not assigned as a mentor for this Interest Group."
            ).get_failure_response(status_code=403)

        serializer = serializers.AvailabilitySlotCreateUpdateSerializer(
            data=request.data, context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Availability slot created successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Mentor Availability'],
        description="Update an existing mentor availability slot.",
        request=serializers.AvailabilitySlotCreateUpdateSerializer,
        responses={200: serializers.AvailabilitySlotCreateUpdateSerializer},
    )
    @role_required([RoleType.MENTOR.value])
    def patch(self, request, slot_id):
        user_id = JWTUtils.fetch_user_id(request)
        slot = MentorAvailabilitySlot.objects.filter(id=slot_id, mentor_user_id=user_id).first()
        
        if not slot:
            return CustomResponse(
                general_message="Availability slot not found."
            ).get_failure_response(status_code=404)
            
        serializer = serializers.AvailabilitySlotCreateUpdateSerializer(
            slot, data=request.data, partial=True, context={"user_id": user_id}
        )
        
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message="Availability slot updated successfully.",
                response=serializer.data
            ).get_success_response()
            
        return CustomResponse(message=serializer.errors).get_failure_response()

    @extend_schema(
        tags=['Dashboard - Mentor Availability'],
        description="Delete a mentor availability slot.",
    )
    @role_required([RoleType.MENTOR.value])
    def delete(self, request, slot_id):
        user_id = JWTUtils.fetch_user_id(request)
        slot = MentorAvailabilitySlot.objects.filter(id=slot_id, mentor_user_id=user_id).first()
        
        if not slot:
            return CustomResponse(
                general_message="Availability slot not found."
            ).get_failure_response(status_code=404)
            
        slot.delete()
        return CustomResponse(
            general_message="Availability slot deleted successfully."
        ).get_success_response()

class MentorPublicAvailabilityAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Mentor Public'],
        description="List active availability slots for a specific mentor.",
        responses={200: serializers.AvailabilitySlotSerializer(many=True)},
    )
    def get(self, request, mentor_id):
        from db.user import UserMentor
        from db.user import MentorApplication
        
        mentor = UserMentor.objects.filter(id=mentor_id).first()
        if not mentor:
            return CustomResponse(
                general_message="Mentor profile not found."
            ).get_failure_response(status_code=404)

        if not MentorApplication.objects.filter(user=mentor.user, status=MentorApplication.Status.APPROVED).exists():
            return CustomResponse(general_message="This user is not an approved mentor.").get_failure_response(status_code=403)

        slots = MentorAvailabilitySlot.objects.filter(mentor_user_id=mentor.user_id, is_active=True)
        serializer = serializers.AvailabilitySlotSerializer(slots, many=True)
        
        return CustomResponse(response=serializer.data).get_success_response()
