from typing import Any, Dict, List

from rest_framework import status
from rest_framework.response import Response
from utils.response import CustomResponse


class InstanceNotFound(CustomResponse):
    def __init__(
        self,
        instance: str = None,
        message: Dict[str, Any] = None,
        general_message: List[str] = None,
        response: Dict[str, Any] = None,
    ) -> None:
        general_message = f"{instance} not found"
        super().__init__(message, general_message, response)

    def get_failure_response(
        self,
        status_code: int = 404,
        http_status_code: int = status.HTTP_404_NOT_FOUND,
    ) -> Response:
        return super().get_failure_response(status_code, http_status_code)
