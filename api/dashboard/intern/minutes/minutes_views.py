import uuid

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.intern import InternGuildMinute

from .serializers import InternGuildMinuteSerializer, InternGuildMinuteCreateUpdateSerializer

# Roles that are allowed to manage (create/update/delete) guild minutes
INTERN_LEAD_ROLES = [RoleType.INTERN_LEAD.value, RoleType.ADMIN.value]


class InternGuildMinuteAPI(APIView):
    """
    Intern Lead's guild minutes endpoint.

    GET    /api/v1/intern/minutes/                    — List minutes (filterable by guild/date)
    POST   /api/v1/intern/minutes/                    — Upload new guild minutes (Intern Lead only)
    PUT    /api/v1/intern/minutes/<minute_id>/        — Edit existing minutes (Intern Lead only)
    DELETE /api/v1/intern/minutes/<minute_id>/        — Delete minutes (Intern Lead only)
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value, RoleType.INTERN_LEAD.value, RoleType.ADMIN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "List guild minutes. Supports optional query filters:\n"
            "- `guild`: Filter by guild name (e.g. 'Frontend Guild')\n"
            "- `date`: Filter by exact date (YYYY-MM-DD)\n"
            "- `page` / `perPage` / `sortBy` for pagination."
        ),
        parameters=[
            OpenApiParameter(name='guild', description='Guild name filter', required=False, type=str),
            OpenApiParameter(name='date', description='Date filter (YYYY-MM-DD)', required=False, type=str),
        ],
        responses={200: InternGuildMinuteSerializer(many=True)},
    )
    def get(self, request, minute_id=None):
        if minute_id:
            minute = InternGuildMinute.objects.filter(id=minute_id).first()
            if not minute:
                return CustomResponse(general_message="Guild minute not found.").get_failure_response()
            serializer = InternGuildMinuteSerializer(minute)
            return CustomResponse(response=serializer.data).get_success_response()

        queryset = InternGuildMinute.objects.select_related('created_by').order_by('-date', 'guild')

        # Optional filters
        guild = request.query_params.get('guild')
        date = request.query_params.get('date')

        if guild:
            queryset = queryset.filter(guild=guild)
        if date:
            queryset = queryset.filter(date=date)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset, request,
            search_fields=['guild', 'title'],
            sort_fields={'date': 'date', 'guild': 'guild'},
        )

        serializer = InternGuildMinuteSerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()

    @role_required(INTERN_LEAD_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Upload daily guild minutes. Restricted to Intern Lead and Admins.",
        request=InternGuildMinuteCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Guild minutes uploaded successfully."),
            400: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = InternGuildMinuteCreateUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return CustomResponse(response=serializer.errors).get_failure_response()

        data = serializer.validated_data
        minute = InternGuildMinute.objects.create(
            id=str(uuid.uuid4()),
            guild=data['guild'],
            date=data['date'],
            title=data['title'],
            minutes=data['minutes'],
            created_by_id=user_id,
            updated_by_id=user_id,
        )

        return CustomResponse(
            general_message="Guild minutes uploaded successfully.",
            response={"id": str(minute.id)},
        ).get_success_response()

    @role_required(INTERN_LEAD_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Edit existing guild minutes. Restricted to Intern Lead and Admins.",
        request=InternGuildMinuteCreateUpdateSerializer,
        responses={
            200: OpenApiResponse(description="Guild minutes updated successfully."),
            404: OpenApiResponse(description="Minute record not found."),
        },
    )
    def put(self, request, minute_id):
        user_id = JWTUtils.fetch_user_id(request)
        minute = InternGuildMinute.objects.filter(id=minute_id).first()

        if not minute:
            return CustomResponse(general_message="Guild minute not found.").get_failure_response()

        serializer = InternGuildMinuteCreateUpdateSerializer(data=request.data, context={'instance_id': minute.id})
        if not serializer.is_valid():
            return CustomResponse(response=serializer.errors).get_failure_response()

        data = serializer.validated_data
        minute.guild = data['guild']
        minute.date = data['date']
        minute.title = data['title']
        minute.minutes = data['minutes']
        minute.updated_by_id = user_id
        minute.save()

        return CustomResponse(general_message="Guild minutes updated successfully.").get_success_response()

    @role_required(INTERN_LEAD_ROLES)
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Delete guild minutes. Restricted to Intern Lead and Admins.",
        responses={
            200: OpenApiResponse(description="Guild minutes deleted successfully."),
            404: OpenApiResponse(description="Minute record not found."),
        },
    )
    def delete(self, request, minute_id):
        minute = InternGuildMinute.objects.filter(id=minute_id).first()

        if not minute:
            return CustomResponse(general_message="Guild minute not found.").get_failure_response()

        minute.delete()
        return CustomResponse(general_message="Guild minutes deleted successfully.").get_success_response()
