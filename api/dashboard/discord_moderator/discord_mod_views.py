from rest_framework.views import APIView
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializer import KarmaActivityLogSerializer
from db.task import KarmaActivityLog
from django.utils import timezone
from utils.utils import DateTimeUtils


class TaskList(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        tasks = KarmaActivityLog.objects.all()
        serializer = KarmaActivityLogSerializer(tasks, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class PendingTasks(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        date = request.query_params.get("date")
        if date:
            tasks = KarmaActivityLog.objects.filter(created_at = date)
            peerpending = tasks.filter(peer_approved = False).count()
            appraiserpending = tasks.filter(appraiser_approved = False).count()
            data = {'peer-pending':peerpending,'appraiser-pending':appraiserpending}
            return CustomResponse(response = data).get_success_response()

        peerpending = KarmaActivityLog.objects.filter(peer_approved = False).count()
        appraiserpending = KarmaActivityLog.objects.filter(appraiser_approved = False).count()
        data = {'peer-pending':peerpending,'appraiser-pending':appraiserpending}
        return CustomResponse(response = data).get_success_response()