from rest_framework.views import APIView
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializer import KarmaActivityLogSerializer
from db.task import KarmaActivityLog
from django.utils import timezone
from utils.utils import DateTimeUtils
from django.db.models import Count, Q


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
            data = {'peer_pending':peerpending,'appraise_pending':appraiserpending}
            return CustomResponse(response = data).get_success_response()

        peerpending = KarmaActivityLog.objects.filter(peer_approved = False).count()
        appraiserpending = KarmaActivityLog.objects.filter(appraiser_approved = False).count()
        data = {'peer_pending':peerpending,'appraise_pending':appraiserpending}
        return CustomResponse(response = data).get_success_response()
    
class LeaderBoard(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        choice = request.query_params.get("option")
        if choice == "peer":
            data = {}
            logs_with_peer_approval = KarmaActivityLog.objects.filter(Q(peer_approved_by__isnull=False) & ~Q(peer_approved_by = ''))
            for obj in logs_with_peer_approval:
                if data.get(obj.peer_approved_by.fullname) == None:
                    data[obj.peer_approved_by.fullname] = {"count":0,"muid":obj.peer_approved_by.muid }
                data[obj.peer_approved_by.fullname]['count']+=1
            return CustomResponse(response=data).get_success_response()
        
        elif choice == "appraiser":
            data = {}
            logs_with_appraiser_approval = KarmaActivityLog.objects.filter(Q(appraiser_approved_by__isnull = False) & ~Q(appraiser_approved_by = ''))
            for obj in logs_with_appraiser_approval:
                if data.get(obj.appraiser_approved_by.fullname) == None:
                    data[obj.appraiser_approved_by.fullname] = {"count":0,"muid":obj.peer_approved_by.muid}
                data[obj.appraiser_approved_by.fullname]['count']+=1
            return CustomResponse(response=data).get_success_response()
        
        else:
            return CustomResponse(response="Bad Request").get_success_response()
    
