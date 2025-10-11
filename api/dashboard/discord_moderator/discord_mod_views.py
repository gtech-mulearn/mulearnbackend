from collections import defaultdict

from django.db.models import Q
from rest_framework.views import APIView

from db.task import KarmaActivityLog
from utils.utils import CommonUtils
from utils.permission import CustomizePermission
from utils.response import CustomResponse
from .serializer import KarmaActivityLogSerializer,LeaderboardSerializer


class TaskList(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        tasks = KarmaActivityLog.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            tasks,
            request,
            ['id', 'full_name', 'task_name', 'status', 'discordlink']
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

    def get(self, request):
        date = request.query_params.get("date")
        if date:
            tasks = KarmaActivityLog.objects.filter(created_at=date)
            peerpending = tasks.filter(peer_approved=False).count()
            appraiserpending = tasks.filter(appraiser_approved=False).count()
            data = {'peer_pending': peerpending,
                    'appraise_pending': appraiserpending}
            return CustomResponse(response=data).get_success_response()

        peerpending = KarmaActivityLog.objects.filter(
            peer_approved=False).count()
        appraiserpending = KarmaActivityLog.objects.filter(
            appraiser_approved=False).count()
        data = {'peer_pending': peerpending,
                'appraise_pending': appraiserpending}
        return CustomResponse(response=data).get_success_response()


class LeaderBoard(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        choice = request.query_params.get("option", "peer")

        approval_field = f"{choice}_approved_by"
        logs_with_approval = KarmaActivityLog.objects.filter(
            Q(**{f"{approval_field}__isnull": False}
              ) & ~Q(**{approval_field: ''})
        )

        data = defaultdict(lambda: {"count": 0, "muid": None})

        for obj in logs_with_approval:
            approver_name = getattr(obj, approval_field).full_name
            if data[approver_name]["muid"] is None:
                data[approver_name]["muid"] = getattr(obj, approval_field).muid
            data[approver_name]["count"] += 1

        response_data = [
            {"name": name, "count": info["count"], "muid": info["muid"]}
            for name, info in data.items()
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

