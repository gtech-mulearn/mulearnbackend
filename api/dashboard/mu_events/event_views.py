from rest_framework.views import APIView
from db.mu_events import MuEvents, MuEventsKarmaRequest
from .event_serializer import (
    MuEventsCreateSerializer,
    MuEventsSerializer,
    MuEventsKarmaRequestSerializer,
    MuEventVerificationSerializer,
)
from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.permission import JWTUtils
from utils.types import RoleType
from datetime import datetime
from db.user import User

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


class MuEventsAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, event_id=None):
        if event_id:
            event = MuEvents.objects.filter(id=event_id).first()
            serializer = MuEventsSerializer(event)
            return CustomResponse(response=serializer.data).get_success_response()
        if not any(
            role.value in JWTUtils.fetch_role(request)
            for role in APPRAISER_VERIFY_ROLES + APPROVAL_ROLES
        ):
            return CustomResponse(
                general_message="You do not have the required role to access this page."
            ).get_failure_response()
        events = MuEvents.objects.all()
        serializer = MuEventsSerializer(events, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = MuEventsCreateSerializer(
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
        event = MuEvents.objects.filter(id=event_id, created_by=user_id).first()
        if not event:
            return CustomResponse(
                general_message="Event not found."
            ).get_failure_response()
        serializer = MuEventsCreateSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.update(event, serializer.validated_data)
            return CustomResponse(
                general_message=f"Event updated successfully",
                response=serializer.validated_data,
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()


class MuEventsVerificationAPI(APIView):
    permission_classes = [CustomizePermission]

    @role_required(roles=[role.value for role in APPRAISER_VERIFY_ROLES])
    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        is_approved = (
            True
            if request.data.get("is_approved") in ("true", "1", "True", True, 1)
            else (
                False
                if request.data.get("is_approved") in ("false", "0", "False", False, 0)
                else None
            )
        )
        serializer = MuEventVerificationSerializer(
            data={
                "suggestions": request.data.get("suggestions", None),
                "user_id": user_id,
                "event_id": event_id,
                "is_approved": is_approved,
            }
        )
        if serializer.is_valid():
            serializer.update(
                serializer.validated_data["event_id"], serializer.validated_data
            )
            return CustomResponse(
                general_message="Status updated",
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()


class MuEventKarmaRequestAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        show_all = str(request.query_params.get("show_all", "0")).lower() in (
            "true",
            "1",
        )
        event = MuEvents.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Event not found."
            ).get_failure_response()
        if show_all:
            if not any(
                role.value in JWTUtils.fetch_role(request)
                for role in APPROVAL_ROLES + APPRAISER_VERIFY_ROLES
            ):
                return CustomResponse(
                    general_message="Not allowed to perform this action."
                ).get_failure_response()
            karma_requests = MuEventsKarmaRequest.objects.filter(event_id=event)
            return CustomResponse(
                response=MuEventsKarmaRequestSerializer(karma_requests, many=True).data
            ).get_success_response()
        karma_request = MuEventsKarmaRequest.objects.filter(
            event_id=event, created_by=user_id
        )
        return CustomResponse(
            response=MuEventsKarmaRequestSerializer(karma_request, many=True).data
        ).get_success_response()

    def post(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = MuEvents.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Event not found."
            ).get_failure_response()
        serializer = MuEventsKarmaRequestSerializer(
            data={
                **{key: value for key, value in request.data.items()},
                "event_id": event_id,
            },
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"Karma request created successfully",
                response=serializer.data,
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    def put(self, request, event_id, karma_request_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = MuEvents.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Event not found."
            ).get_failure_response()
        karma_request = MuEventsKarmaRequest.objects.filter(
            id=karma_request_id, event_id=event, user_id=user_id
        ).first()
        if not karma_request:
            return CustomResponse(
                general_message="Karma request not found."
            ).get_failure_response()
        serializer = MuEventsKarmaRequestSerializer(
            karma_request, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"Karma request updated successfully",
                response=serializer.data,
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()


class MuEventKarmaRequestVerificationAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, event_id, karma_request_id):
        user_id = JWTUtils.fetch_user_id(request)
        event = MuEvents.objects.filter(id=event_id).first()
        is_appraiser = request.data.get("is_appraiser")
        verified = request.data.get("verified")
        suggestions = request.data.get("suggestions")
        if not event:
            return CustomResponse(
                general_message="Event not found."
            ).get_failure_response()
        karma_request = MuEventsKarmaRequest.objects.filter(
            id=karma_request_id, event_id=event, user_id=user_id
        ).first()
        if not karma_request:
            return CustomResponse(
                general_message="Karma request not found."
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

        if is_appraiser:
            karma_request.suggestions += f"\nAppraiser:\n{suggestions}"
            karma_request.is_approved = verified
            karma_request.appraised_by = user_id
            karma_request.appraised_at = datetime.now()
            karma_request.save()
            return CustomResponse(
                general_message=f"Karma request verified successfully",
                response=MuEventsKarmaRequestSerializer(karma_request).data,
            ).get_success_response()
        karma_request.suggestions = suggestions
        karma_request.is_approved = verified
        karma_request.approved_by = user_id
        karma_request.approved_at = datetime.now()
        karma_request.save()
        return CustomResponse(
            general_message=f"Karma request approved successfully",
            response=MuEventsKarmaRequestSerializer(karma_request).data,
        ).get_success_response()
