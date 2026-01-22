from rest_framework.views import APIView

from db.task import Events
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .events_serializer import EventsCUDSerializer, EventsListSerializer
from utils.types import RoleType
from utils.permission import role_required

class EventAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id=None):
        # If event_id is provided, return single event
        if event_id:
            event = Events.objects.filter(id=event_id).first()
            if not event:
                return CustomResponse(
                    general_message="Invalid Event id"
                ).get_failure_response()
            
            serializer = EventsListSerializer(event)
            return CustomResponse(
                general_message="Event retrieved successfully",
                response=serializer.data
            ).get_success_response()
        
        # Otherwise, return paginated list of all events
        events = Events.objects.exclude(status=Events.Status.CANCELLED.value)
        paginated_queryset = CommonUtils.get_paginated_queryset(
            events,
            request,
            ['id', 'name']
        )

        serializer = EventsListSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get(
                "pagination"
            )
        )
    
    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = EventsCUDSerializer(
            data=request.data,
            context={
                "user_id": user_id,
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{request.data.get('name')} Event created successfully",
                response=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()

    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    def put(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        events = Events.objects.filter(id=event_id).first()

        if events is None:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()

        serializer = EventsCUDSerializer(
            events,
            data=request.data,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{events.name} Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    def patch(self,request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        events = Events.objects.filter(id=event_id).first()

        if events is None:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()

        serializer = EventsCUDSerializer(
            events,
            data=request.data,
            partial=True,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{events.name} Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    @role_required(
        [
            RoleType.ADMIN.value,
        ]
    )
    def delete(self, request, event_id):

        events = Events.objects.filter(id=event_id).first()

        if events is None:
            return CustomResponse(
                general_message="Invalid event id"
            ).get_failure_response()

        events.status = Events.Status.CANCELLED.value
        events.save()

        return CustomResponse(
            general_message=f"{events.name} Status changed to Cancelled"
        ).get_success_response()
