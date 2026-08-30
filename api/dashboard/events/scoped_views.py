"""
Scoped Event Feed views.
Each view returns published events filtered to a specific entity scope.
"""
from rest_framework.views import APIView

from db.events import Event
from db.task import InterestGroup
from db.organization import Organization
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils

from .serializers import EventListItemSerializer, get_active_events
from drf_spectacular.utils import extend_schema


def _viewer_id(request):
    try:
        return JWTUtils.fetch_user_id(request)
    except Exception:
        return None


class IGEventListAPI(APIView):
    """
    GET /events/ig/<ig_id>/
    All published events organised by or scoped to a specific IG.
    Includes both global-IG events and all campus chapter events for that IG.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve I G Event List.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request, ig_id):
        ig = InterestGroup.objects.filter(id=ig_id.strip()).first()
        if not ig:
            return CustomResponse(general_message='Interest Group not found.').get_failure_response()

        from django.db.models import Q
        events = get_active_events().select_related('category', 'organiser_ig', 'organiser_org').filter(
            Q(organiser_ig_id=ig_id) | Q(scope_ig_id=ig_id),
        )

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'venue_city'],
            sort_fields={'start_datetime': 'start_datetime'},
        )
        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': _viewer_id(request), 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class ClusterEventListAPI(APIView):
    """
    GET /events/ig/cluster/<cluster>/
    All published events from IGs in a given cluster.
    Cluster maps to the InterestGroup.category field
    (values: coder | maker | manager | creative | others).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Cluster Event List.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request, cluster):
        ig_ids = list(
            InterestGroup.objects.filter(category__iexact=cluster)
            .values_list('id', flat=True)
        )

        if not ig_ids:
            return CustomResponse().paginated_response(
                data=[],
                pagination={'count': 0, 'totalPages': 0, 'isNext': False, 'isPrev': False, 'nextPage': None},
            )

        events = get_active_events().select_related('category', 'organiser_ig', 'organiser_org').filter(
            organiser_ig_id__in=ig_ids,
        )

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'venue_city'],
            sort_fields={'start_datetime': 'start_datetime'},
        )
        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': _viewer_id(request), 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class CampusEventListAPI(APIView):
    """
    GET /events/campus/<campus_id>/
    All published events scoped to or organised by a specific campus.
    Supports ?cluster= to further filter by IG cluster.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Campus Event List.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request, campus_id):
        org = Organization.objects.filter(id=campus_id.strip()).first()
        if not org:
            return CustomResponse(general_message='Campus not found.').get_failure_response()

        from django.db.models import Q
        events = get_active_events().select_related('category', 'organiser_ig', 'organiser_org').filter(
            Q(scope_org_id=campus_id) | Q(organiser_org_id=campus_id),
        )

        # Optional cluster filter
        if cluster := request.query_params.get('cluster'):
            ig_ids = list(
                InterestGroup.objects.filter(category__iexact=cluster)
                .values_list('id', flat=True)
            )
            events = events.filter(organiser_ig_id__in=ig_ids)

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'venue_city'],
            sort_fields={'start_datetime': 'start_datetime'},
        )
        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': _viewer_id(request), 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class CampusIGEventListAPI(APIView):
    """
    GET /events/campus-ig/<campus_ig_id>/
    Events created by a specific campus IG chapter only.
    campus_ig_id corresponds to the organiser_ci_id on events.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Campus I G Event List.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request, campus_ig_id):
        events = get_active_events().select_related('category', 'organiser_ig', 'organiser_org').filter(
            organiser_ci_id=campus_ig_id,
        )

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'venue_city'],
            sort_fields={'start_datetime': 'start_datetime'},
        )
        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': _viewer_id(request), 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )


class CompanyEventListAPI(APIView):
    """
    GET /events/company/<company_id>/
    All published events organised by a specific company/partner.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve Company Event List.",
        responses={200: EventListItemSerializer},
    )
    def get(self, request, company_id):
        org = Organization.objects.filter(id=company_id.strip()).first()
        if not org:
            return CustomResponse(general_message='Company not found.').get_failure_response()

        events = get_active_events().select_related('category', 'organiser_ig', 'organiser_org').filter(
            organiser_org_id=company_id,
            organiser_type=Event.OrganiserType.COMPANY,
        )

        paginated = CommonUtils.get_paginated_queryset(
            events, request,
            search_fields=['title', 'venue_city'],
            sort_fields={'start_datetime': 'start_datetime'},
        )
        serializer = EventListItemSerializer(
            paginated['queryset'], many=True,
            context={'user_id': _viewer_id(request), 'request': request},
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated['pagination'],
        )
