from django.db.models import Count, F, Min, Q
from rest_framework.views import APIView

from db.task import KarmaActivityLog
from utils.utils import CommonUtils
from utils.permission import CustomizePermission
from utils.response import CustomResponse
from .serializer import KarmaActivityLogSerializer,LeaderboardSerializer
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


class TaskList(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Discord Moderator'],
        description="Retrieve Task List.",
        responses={200: KarmaActivityLogSerializer},
    )
    def get(self, request):
        # The serializer reads user.full_name and task.title / discord_link.
        tasks = KarmaActivityLog.objects.select_related("user", "task")
        paginated_queryset = CommonUtils.get_paginated_queryset(
            tasks,
            request,
            # Model paths of the serializer fields. The old list used the
            # serializer names (full_name, task_name, ...), which are not model
            # fields, so any ?search= raised FieldError. "status" is computed
            # from two booleans and is not searchable.
            ['id', 'user__full_name', 'task__title', 'task__discord_link']
        )

        serializer = KarmaActivityLogSerializer(
            paginated_queryset.get("queryset"), 
            many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,      
            pagination=paginated_queryset.get(
                "pagination"
            )
        )

class PendingTasks(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Dashboard - Discord Moderator'], description="Retrieve Pending Tasks.",
        responses={200: inline_serializer(
            name='DiscordPendingTasksResponse',
            fields={
                'peer_pending': s.IntegerField(),
                'appraise_pending': s.IntegerField(),
            },
        )},
    )
    def get(self, request):
        date = request.query_params.get("date")
        tasks = KarmaActivityLog.objects.all()
        if date:
            tasks = tasks.filter(created_at=date)
        # Both counts in one pass over the table instead of two full scans.
        counts = tasks.aggregate(
            peer_pending=Count("id", filter=Q(peer_approved=False)),
            appraise_pending=Count("id", filter=Q(appraiser_approved=False)),
        )
        data = {'peer_pending': counts["peer_pending"],
                'appraise_pending': counts["appraise_pending"]}
        return CustomResponse(response=data).get_success_response()


class LeaderBoard(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Discord Moderator'],
        description="Retrieve Leader Board.",
        responses={200: LeaderboardSerializer},
    )
    def get(self, request):
        choice = request.query_params.get("option", "peer")
        # The option is interpolated into a field name, so only the two real
        # approval fields are accepted (anything else raised FieldError -> 500).
        if choice not in ("peer", "appraiser"):
            return CustomResponse(
                general_message="option must be 'peer' or 'appraiser'"
            ).get_failure_response()

        approval_field = f"{choice}_approved_by"
        logs_with_approval = KarmaActivityLog.objects.filter(
            Q(**{f"{approval_field}__isnull": False}
              ) & ~Q(**{approval_field: ''})
        )

        # One GROUP BY instead of iterating the whole karma log in Python with a
        # User query per row. Grouped by name, as before (approvers sharing a
        # name are merged); muid is the smallest of theirs. Highest count first.
        response_data = [
            {"name": row["name"], "count": row["count"], "muid": row["muid"]}
            for row in logs_with_approval.values(name=F(f"{approval_field}__full_name"))
            .annotate(count=Count("id"), muid=Min(f"{approval_field}__muid"))
            .order_by("-count", "name")
        ]

        paginated_queryset = CommonUtils.get_paginated_queryset(
            response_data,
            request,
            []
        )
        serializer = LeaderboardSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get(
                "pagination"
            )
        )

