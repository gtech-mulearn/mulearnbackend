from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from db.events import Event
from db.task import InterestGroup
from db.organization import Organization
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import OrganizationType

from . import serializers


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class EventListCreateAPI(APIView):
    """
    Unified Events API - List and Create

    Endpoints:
        GET  /api/events - List events with filtering
        POST /api/events - Create new event
    """
    authentication_classes = [CustomizePermission]

    def get(self, request):
        """
        Get events with filtering

        Query Parameters:
            - type: Event scope (campus, ig, global, etc.)
            - campus: Campus/Organization ID
            - ig: Interest Group ID
            - status: Event status (draft, published, ongoing, etc.)
            - title: Search by title
            - page: Page number for pagination
            - page_size: Number of events per page
        """
        queryset = Event.objects.all().select_related(
            "created_by", "scope_org", "scope_ig", "category", "updated_by"
        ).order_by("-created_at")

        # Filter by scope/type
        event_type = request.query_params.get("type")
        if event_type:
            queryset = queryset.filter(scope=event_type)

        # Filter by campus
        campus_id = request.query_params.get("campus")
        if campus_id:
            queryset = queryset.filter(scope_org_id=campus_id)

        # Filter by IG (Interest Group)
        ig_id = request.query_params.get("ig")
        if ig_id:
            queryset = queryset.filter(scope_ig_id=ig_id)

        # Filter by status
        status = request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Search by title
        title = request.query_params.get("title")
        if title:
            queryset = queryset.filter(Q(title__icontains=title) | Q(description__icontains=title))

        # Pagination
        paginator = StandardResultsSetPagination()
        paginated_queryset = paginator.paginate_queryset(queryset, request)

        serializer = serializers.EventListSerializer(paginated_queryset, many=True)

        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": {
                    "count": paginator.page.paginator.count,
                    "next": paginator.get_next_link(),
                    "previous": paginator.get_previous_link(),
                    "page_size": paginator.page_size,
                }
            }
        ).get_success_response()

    def post(self, request):
        """
        Create a new event

        Request body:
        {
            "title": "Event Title",
            "slug": "event-title-unique",
            "description": "Event description",
            "scope": "campus",
            "scope_org": "org-id",
            "scope_ig": "ig-id",
            "start_datetime": "2026-04-15T10:00:00Z",
            "end_datetime": "2026-04-15T12:00:00Z",
            "venue_type": "hybrid",
            "venue_city": "Bangalore",
            ...
        }
        """
        user_id = JWTUtils.fetch_user_id(request)

        serializer = serializers.EventCreateUpdateSerializer(
            data=request.data,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            event = serializer.save()
            response_serializer = serializers.EventDetailSerializer(event)
            return CustomResponse(response=response_serializer.data).get_success_response()

        return CustomResponse(
            general_message="Invalid event data",
            error=serializer.errors
        ).get_failure_response()


class EventDetailAPI(APIView):
    """
    Unified Events API - Get, Update, Delete

    Endpoints:
        GET    /api/events/:id - Get event details
        PATCH  /api/events/:id - Update event
        DELETE /api/events/:id - Delete event
    """
    authentication_classes = [CustomizePermission]

    def get(self, request, event_id):
        """
        Get event details

        Args:
            event_id: Event ID

        Returns:
            Detailed event information
        """
        event = Event.objects.filter(id=event_id).select_related(
            "created_by", "updated_by", "scope_org", "scope_ig",
            "organiser_org", "organiser_ig", "category"
        ).first()

        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        serializer = serializers.EventDetailSerializer(event)
        return CustomResponse(response=serializer.data).get_success_response()

    def patch(self, request, event_id):
        """
        Update event fields

        Args:
            event_id: Event ID

        Request body: Only include fields to update
        """
        event = Event.objects.filter(id=event_id).first()

        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)

        # Optionally check if user is creator
        # if event.created_by_id != user_id:
        #     return CustomResponse(
        #         general_message="Only event creator can update"
        #     ).get_failure_response()

        serializer = serializers.EventCreateUpdateSerializer(
            event,
            data=request.data,
            partial=True,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            updated_event = serializer.save()
            response_serializer = serializers.EventDetailSerializer(updated_event)
            return CustomResponse(response=response_serializer.data).get_success_response()

        return CustomResponse(
            general_message="Invalid event data",
            error=serializer.errors
        ).get_failure_response()

    def delete(self, request, event_id):
        """
        Delete an event

        Args:
            event_id: Event ID
        """
        event = Event.objects.filter(id=event_id).first()

        if not event:
            return CustomResponse(
                general_message="Event not found"
            ).get_failure_response()

        user_id = JWTUtils.fetch_user_id(request)

        # Optionally check if user is creator
        # if event.created_by_id != user_id:
        #     return CustomResponse(
        #         general_message="Only event creator can delete"
        #     ).get_failure_response()

        event_title = event.title
        event.delete()

        return CustomResponse(
            general_message=f"Event '{event_title}' deleted successfully"
        ).get_success_response()
