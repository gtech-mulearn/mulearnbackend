from decouple import config
from rest_framework.views import APIView
from django.http import FileResponse
from utils.permission import CustomizePermission, role_required
from utils.types import RoleType

log_path = config("LOGGER_DIR_PATH")


class ErrorLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value])
    def get(self, request):
        error_log = f"{log_path}/error.log"
        response = FileResponse(open(error_log, 'rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="error.log"'
        return response
