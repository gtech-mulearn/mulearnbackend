from rest_framework.views import APIView
from db.events import Event, EventKarmaRequest
from .event_serializer import EventCreateSerializer, EventSerializer
from utils.permission import CustomizePermission
from utils.response import CustomResponse
from utils.permission import JWTUtils, role_required
from utils.types import RoleType
from datetime import datetime

APPROVAL_ROLES = [
    RoleType.DISCORD_MANAGER,
    RoleType.ENABLER,
    RoleType.IG_LEAD,
]

APPRAISER_VERIFY_ROLES = [
    RoleType.ADMIN,
    RoleType.ASSOCIATE,
    RoleType.MENTOR,
    RoleType.APPRAISER,
]


class EventAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, event_id=None):
        if event_id:
            event = Event.objects.get(id=event_id)
            serializer = EventSerializer(event)
            return CustomResponse(response=serializer.data).get_success_response()
        if not any(
            role.value in JWTUtils.fetch_role(request)
            for role in APPRAISER_VERIFY_ROLES + APPROVAL_ROLES
        ):
            return CustomResponse(
                general_message="You do not have the required role to access this page."
            ).get_failure_response()
        events = Event.objects.all()
        events = Event.objects.all()
        serializer = EventSerializer(events, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = EventCreateSerializer(
            data=request.data, context={"user_id": user_id}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"{request.data.get('name')} Event created successfully",
                response=serializer.data,
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    def put(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = Event.objects.get(id=event_id, created_by=user_id)
        if not event:
            return CustomResponse(
                general_message="Event not found."
            ).get_failure_response()
        serializer = EventCreateSerializer(event, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"{request.data.get('name')} Event updated successfully",
                response=serializer.data,
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()


class EventVerificationAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event_id = request.data.get("event_id")
        is_verified = request.data.get("is_verified")
        suggestions = request.data.get("suggestions")
        is_appraiser = request.data.get("is_appraiser")
        event = Event.objects.get(id=event_id)
        if not event:
            return CustomResponse(
                general_message="Event not found."
            ).get_failure_response()
        if is_appraiser and not any(
            role.value in JWTUtils.fetch_role(request)
            for role in APPRAISER_VERIFY_ROLES
        ):
            return CustomResponse(
                general_message="You do not have the required role to access this page."
            ).get_failure_response()
        if not is_appraiser and not any(
            role.value in JWTUtils.fetch_role(request)
            for role in APPROVAL_ROLES + APPRAISER_VERIFY_ROLES
        ):
            return CustomResponse(
                general_message="You do not have the required role to access this page."
            ).get_failure_response()
        event.suggestions = suggestions
        if is_appraiser:
            event.appraised_by = user_id
            event.appraised_at = datetime.now()
            event.save()
            return CustomResponse(
                general_message=f"{event.name} Event appraised successfully",
                response=EventSerializer(event).data,
            ).get_success_response()
        event.is_approved = is_verified
        event.approved_by = user_id
        event.approved_at = datetime.now()
        event.save()
        return CustomResponse(
            general_message=f"{event.name} Event approved successfully",
            response=EventSerializer(event).data,
        ).get_success_response()
