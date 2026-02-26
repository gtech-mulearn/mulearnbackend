from rest_framework.views import APIView

from db.task import Events
from db.company import Company
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


class CompanyEventAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    def _get_company(self, user_id):
        return Company.objects.filter(company_user_id=user_id).first()
    
    def _check_ownership(self, request_company, event):
        """
        Returns (is_allowed, error_message).
        - Resolves creator company once using already-fetched request_company.
        - Returns False with clear message if event was Admin-created (no company).
        """
        creator_company = self._get_company(event.created_by_id)
        if not creator_company:
            return False, "This event was not created by a company user"
        if request_company.id != creator_company.id:
            return False, "You are not allowed to modify this event"
        return True, None

    @role_required([RoleType.COMPANY.value])
    def get(self, request, event_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        
        company = self._get_company(user_id)
        if not company:
            return CustomResponse(
                general_message="Only company users can view company events"
            ).get_unauthorized_response()

        # Single event by ID
        if event_id:
            event = Events.objects.filter(id=event_id).first()
            if not event:
                return CustomResponse(
                    general_message="Invalid Event id"
                ).get_failure_response()

            is_allowed, error = self._check_ownership(company, event)
            if not is_allowed:
                return CustomResponse(
                    general_message=error
                ).get_unauthorized_response()

            serializer = EventsListSerializer(event)
            return CustomResponse(response=serializer.data).get_success_response()

        # List all company events
        # Get all users from this company
        company_user_ids = [company.company_user_id_id]  # Start with main company user
        
        # Filter events created by any user from this company
        events = Events.objects.filter(
            created_by_id__in=company_user_ids
        ).exclude(
            status=Events.Status.CANCELLED.value
        ).order_by('-created_at')

        # Pagination
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
            pagination=paginated_queryset.get("pagination")
        )

    # ...existing post/patch/delete methods...
    
    @role_required([RoleType.COMPANY.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        company = self._get_company(user_id)
        if not company:
            return CustomResponse(
                general_message="Only company users can create events"
            ).get_unauthorized_response()

        serializer = EventsCUDSerializer(
            data=request.data,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"{request.data.get('name')} Event created successfully",
                response=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.COMPANY.value])
    def patch(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        company = self._get_company(user_id)
        if not company:
            return CustomResponse(
                general_message="Only company users can edit events"
            ).get_unauthorized_response()

        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()

        if event.status == Events.Status.CANCELLED.value:
            return CustomResponse(
                general_message="Cannot modify a cancelled event"
            ).get_failure_response()

        is_allowed, error = self._check_ownership(company, event)
        if not is_allowed:
            return CustomResponse(
                general_message=error
            ).get_unauthorized_response()

        serializer = EventsCUDSerializer(
            event,
            data=request.data,
            partial=True,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message=f"{event.name} Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors
        ).get_failure_response()

    @role_required([RoleType.COMPANY.value])
    def delete(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)

        company = self._get_company(user_id)
        if not company:
            return CustomResponse(
                general_message="Only company users can delete events"
            ).get_unauthorized_response()

        event = Events.objects.filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message="Invalid Event id"
            ).get_failure_response()

        if event.status == Events.Status.CANCELLED.value:
            return CustomResponse(
                general_message="Event is already cancelled"
            ).get_failure_response()

        is_allowed, error = self._check_ownership(company, event)
        if not is_allowed:
            return CustomResponse(
                general_message=error
            ).get_unauthorized_response()

        event.status = Events.Status.CANCELLED.value
        event.updated_by_id = user_id
        event.save(update_fields=["status", "updated_by", "updated_at"])

        return CustomResponse(
            general_message=f"{event.name} Status changed to Cancelled"
        ).get_success_response()
