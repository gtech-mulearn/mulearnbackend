import logging
import os

from django.conf import settings
from django.http import FileResponse
from rest_framework.views import APIView

from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.types import RoleType

from .log_helper import ManageURLPatterns, logHandler


class DownloadErrorLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def get(self, request, log_name):
        error_log = f"{settings.LOG_PATH}/{log_name}.log"
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
        error_log = f"{settings.LOG_PATH}/{log_name}.log"
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
        error_log = f"{settings.LOG_PATH}/{log_name}.log"
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
    """
    API view for logging errors.

    Args:
        request: The HTTP request object.

    Returns:
        CustomResponse: The response object containing formatted error logs.

    Raises:
        IOError: If there is an error reading the error log file.

    Examples:
        >>> logger_api = LoggerAPI()
        >>> response = logger_api.get(request)
    """

    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def get(self, request):
        """
        Get the error logs.

        Args:
            request: The HTTP request object.

        Returns:
            CustomResponse: The response object containing formatted error logs.

        Raises:
            IOError: If there is an error reading the error log file.

        Examples:
            >>> logger_api = LoggerAPI()
            >>> response = logger_api.get(request)
        """
        error_log = f"{settings.LOG_PATH}/error.log"
        try:
            with open(error_log, "r") as file:
                log_data = file.read()
        except IOError as e:
            return CustomResponse(response=str(e)).get_failure_response()

        log_handler = logHandler(log_data)
        formatted_errors = log_handler.parse_logs()
        return CustomResponse(response=formatted_errors).get_success_response()

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def patch(self, request, error_id):
        """
        Patch the error log.

        Args:
            request: The HTTP request object.
            error_id: The ID of the error to be marked as patched.

        Returns:
            CustomResponse: The response object indicating the success of the patch.

        Examples:
            >>> logger_api = LoggerAPI()
            >>> response = logger_api.patch(request, error_id)
        """
        logger = logging.getLogger("django")
        logger.error(f"PATCHED : {error_id}")
        return CustomResponse(response="Updated patch list").get_success_response()


class ErrorGraphAPI(APIView):
    """
    A class representing the ErrorGraphAPI view.

    This view handles the GET request to retrieve formatted error data including a heatmap of URL hits,
    incident information, and affected users. It requires authentication and specific roles to access.

    Args:
        self: The instance of the class itself.
    """

    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def get(self, request):
        """
        Handle the GET request to retrieve formatted error data.

        Returns:
            CustomResponse: The success response containing the formatted error data.

        Raises:
            IOError: If an error occurs while reading the error log file.

        """
        try:
            error_log = f"{settings.LOG_PATH}/error.log"

            with open(error_log, "r") as file:
                log_data = file.read()

            log_handler = logHandler(log_data)

            formatted_errors = {
                "heatmap": log_handler.get_urls_heatmap(),
                "incident_info": log_handler.get_incident_info(),
                "affected_users": log_handler.get_affected_users(),
            }

            return CustomResponse(response=formatted_errors).get_success_response()

        except IOError as e:
            return CustomResponse(response=str(e)).get_failure_response()


class ErrorTabAPI(APIView):
    """
    A class representing the ErrorTabAPI view.

    This view handles the GET request to retrieve grouped URL patterns based on user roles.
    It requires authentication and specific roles to access.

    Args:
        self: The instance of the class itself.
    """

    authentication_classes = [CustomizePermission]

    @role_required(
        [RoleType.ADMIN.value, RoleType.FELLOW.value, RoleType.TECH_TEAM.value]
    )
    def get(self, request):
        """
        Handle the GET request to retrieve grouped URL patterns.

        Returns:
            CustomResponse: The success response containing the grouped URL patterns.

        Raises:
            IOError: If an error occurs while retrieving the URL patterns.

        """
        try:
            error_log = f"{settings.LOG_PATH}/error.log"

            with open(error_log, "r") as file:
                log_data = file.read()

            log_handler = logHandler(log_data)
            parsed_errors = log_handler.parse_logs()
        
            urlpatterns = ManageURLPatterns().urlpatterns
            grouped_patterns = ManageURLPatterns.group_patterns(urlpatterns)

            return CustomResponse(response=parsed_errors).get_success_response()

        except IOError as e:
            return CustomResponse(response=str(e)).get_failure_response()
