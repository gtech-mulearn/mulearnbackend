import logging
import os

from decouple import config
from django.http import FileResponse
from rest_framework.views import APIView

from api.dashboard.error_log.log_helper import logHandler
from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.types import RoleType

LOG_PATH = config("LOGGER_DIR_PATH")


class DownloadErrorLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def get(self, request, log_name):
        error_log = f"{LOG_PATH}/{log_name}.log"
        if os.path.exists(error_log):
            response = FileResponse(
                open(error_log, "rb"), content_type="application/octet-stream"
            )
            response["Content-Disposition"] = f'attachment; filename="{log_name}"'
            return response
        return CustomResponse(
            general_message=f"{log_name} Not Found"
        ).get_failure_response()


class ViewErrorLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def get(self, request, log_name):
        error_log = f"{LOG_PATH}/{log_name}.log"
        if os.path.exists(error_log):
            try:
                with open(error_log, "r") as log_file:
                    log_content = log_file.read()
                return CustomResponse(response=log_content).get_success_response()
            except Exception as e:
                return CustomResponse(
                    general_message="Error reading log file"
                ).get_failure_response()

        return CustomResponse(
            general_message=f"{log_name} Not Found"
        ).get_failure_response()


class ClearErrorLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def post(self, request, log_name):
        error_log = f"{LOG_PATH}/{log_name}.log"
        if os.path.exists(error_log):
            try:
                with open(error_log, "w") as log_file:
                    log_file.truncate(0)
                return CustomResponse(
                    general_message=f"{log_name} log cleared successfully"
                ).get_success_response()
            except Exception as e:
                print(e)
                return CustomResponse(
                    general_message="Error reading log file"
                ).get_failure_response()

        return CustomResponse(
            general_message=f"{log_name} Not Found"
        ).get_failure_response()


class LoggerAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def get(self, request):
        error_log = f"{LOG_PATH}/error.log"
        try:
            with open(error_log, "r") as file:
                log_data = file.read()
        except IOError as e:
            return CustomResponse(response=str(e)).get_failure_response()
        
        log_handler = logHandler()
        formatted_errors = log_handler.parse_logs(log_data)
        return CustomResponse(response=formatted_errors).get_success_response()
    
    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def patch(self, request, error_id):
        logger = logging.getLogger("django")
        logger.error(f"PATCHED : {error_id}")
        return CustomResponse(response="Updated patch list").get_success_response()
