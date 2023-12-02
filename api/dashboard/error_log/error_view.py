import os

from decouple import config
from django.http import FileResponse
from rest_framework.views import APIView

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
    def get(self, request):
        import re

        error_log = f"{LOG_PATH}/error.log"
        # Define the regex pattern
        pattern = (
            r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:"
            r".*?(?=\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} ERROR EXCEPTION INFO:|\Z)"
        )

        # Read the file
        with open(error_log, "r") as file:
            log_data = file.read()

        # Find all matches
        matches = re.findall(pattern, log_data, re.DOTALL)
        formatted_errors = {}

        id_pattern = r"ID: (.+?)\n(?=TYPE:)"
        timestamp_pattern = r"^(.+?) ERROR.*"
        type_pattern = r"TYPE: (.+?)\n(?=MESSAGE:)"
        message_pattern = r"MESSAGE: (.+?)\n(?=METHOD:)"
        method_pattern = r"METHOD: (.+?)\n(?=PATH:)"
        path_pattern = r"PATH: (.+?)\n(?=AUTH:)"
        auth_pattern = r"AUTH: \n(.+?)\n(?=BODY:)"
        body_pattern = r"BODY: \n(.+?)\n(?=TRACEBACK:)"
        traceback_pattern = r"TRACEBACK: (.+)$"
        
        from datetime import datetime

        for error in matches:

            # Extract information using regex
            extracted_id = re.search(id_pattern, error, re.DOTALL).group(1)
            extracted_type = re.search(type_pattern, error, re.DOTALL).group(1)
            extracted_timestamp = re.search(timestamp_pattern, error, re.DOTALL).group(1)
            extracted_message = re.search(message_pattern, error, re.DOTALL).group(1)
            extracted_method = re.search(method_pattern, error, re.DOTALL).group(1)
            extracted_path = re.search(path_pattern, error, re.DOTALL).group(1)
            extracted_auth = (
                auth.group(1)
                if (auth := re.search(auth_pattern, error, re.DOTALL))
                else None
            )
            extracted_body = (
                body.group(1)
                if (body := re.search(body_pattern, error, re.DOTALL))
                else None
            )
            extracted_traceback = (
                re.search(traceback_pattern, error, re.DOTALL).group(1).strip()
            )
            
            timestamp_str = extracted_timestamp.replace(',', '.')

            # Define the format of your timestamp string
            timestamp_format = "%Y-%m-%d %H:%M:%S.%f"

            # Use the strptime method to parse the string into a datetime object
            timestamp_datetime = datetime.strptime(timestamp_str, timestamp_format)

            if extracted_id not in formatted_errors:
                formatted_errors[extracted_id] = {
                    "id": "",
                    "type": set(),
                    "timestamps": set(),
                    "message": set(),
                    "method": set(),
                    "path": set(),
                    "auth": set(),
                    "body": set(),
                    "traceback": set(),
                }
                formatted_errors[extracted_id]["id"] = extracted_id

            formatted_errors[extracted_id]["type"].add(extracted_type)
            formatted_errors[extracted_id]["timestamps"].add(timestamp_datetime)
            formatted_errors[extracted_id]["message"].add(extracted_message)
            formatted_errors[extracted_id]["method"].add(extracted_method)
            formatted_errors[extracted_id]["path"].add(extracted_path)
            if extracted_auth:
                formatted_errors[extracted_id]["auth"].add(extracted_auth)
            if extracted_body:
                formatted_errors[extracted_id]["body"].add(extracted_body)
            formatted_errors[extracted_id]["traceback"].add(extracted_traceback)

        return CustomResponse(response=formatted_errors.values()).get_success_response()