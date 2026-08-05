from rest_framework.views import APIView
from django.db.models import Count

from db.task import TaskReport, KarmaActivityLog
from utils.response import CustomResponse
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.types import RoleType
from . import serializers
from drf_spectacular.utils import extend_schema

class TaskReportInfoView(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, RoleType.FELLOW])
    @extend_schema(
        tags=['Dashboard - Task Report'],
        description="Retrieve Task Report Info.",
        responses={200: serializers.TaskReportSerializer},
    )
    def get(self, request):
        reports = TaskReport.objects.all()
        
        # Filtering
        if status := request.query_params.get("status"):
            reports = reports.filter(status=status)

        serializer = serializers.TaskReportSerializer(reports, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN, RoleType.FELLOW])
    @extend_schema(
        tags=['Dashboard - Task Report'],
        description="Update Task Report Info.",
        responses={200: serializers.TaskReportUpdateSerializer},
    )
    def put(self, request, report_id):
        report = TaskReport.objects.filter(id=report_id).first()
        if not report:
            return CustomResponse(general_message="Report not found").get_failure_response()

        serializer = serializers.TaskReportUpdateSerializer(
            report, data=request.data, context={"user_id": JWTUtils.fetch_user_id(request)}
        )
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message="Report status updated successfully").get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class TaskReportTaskGroupingView(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, RoleType.FELLOW])
    @extend_schema(tags=['Dashboard - Task Report'], description="Retrieve Task Report Task Grouping.",
        responses={200: TaskReportSerializer},
    )
    def get(self, request):
        # 1) How many people reported to each tasks
        # Group by message_id
        report_counts = (
            TaskReport.objects.values("message_id")
            .annotate(report_count=Count("id"))
            .order_by("-report_count")
        )
        
        data = []
        for item in report_counts:
            res = {
                "message_id": item["message_id"],
                "report_count": item["report_count"],
                "task_hashtag": None
            }
            # Try to fetch hashtag from KarmaActivityLog
            if kal := KarmaActivityLog.objects.filter(task_message_id=item["message_id"]).first():
                res["task_hashtag"] = kal.task.hashtag
            
            data.append(res)

        return CustomResponse(response=data).get_success_response()


class TaskReportReporterGroupingView(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, RoleType.FELLOW])
    @extend_schema(tags=['Dashboard - Task Report'], description="Retrieve Task Report Reporter Grouping.",
        responses={200: TaskReportSerializer},
    )
    def get(self, request):
        # Request #2: "How many tasks were reported by a person" - confusing phrasing
        # It could mean "How many reports did User X make" OR "How many times was User Y reported"
        # Let's provide both.
        
        # Reports by Reporter
        reporters = (
            TaskReport.objects.values("reporter__id", "reporter__fullname")
            .annotate(report_count=Count("id"))
            .order_by("-report_count")
        )
        
        # Reports against Offender
        offenders = (
            TaskReport.objects.values("offender__id", "offender__fullname")
            .annotate(report_count=Count("id"))
            .order_by("-report_count")
        )

        return CustomResponse(
            response={"reporters": reporters, "offenders": offenders}
        ).get_success_response()
