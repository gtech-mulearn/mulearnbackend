from typing import Any, Dict, List

from rest_framework import status
from rest_framework.response import Response

from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse


class CustomResponse:
    """A custom response class for API views.

    Attributes:
        message (Dict[str, Any]): A dictionary of messages.
        response (Dict[str, Any]): A dictionary of response data.
    """

    def __init__(
            self,
            message: Dict[str, Any] = None,
            general_message: List[str] = None,
            response: Dict[str, Any] = None,
    ) -> None:
        """Initializes the CustomResponse object.

        Args:
            message (Dict[str, Any], optional): A dictionary of messages.
                Defaults to {}.
            general_message (List[str], optional): A list of general messages.
                Defaults to [].
            response (Dict[str, Any], optional): A dictionary of response data.
                Defaults to {}.
        """
        self.message = {} if message is None else message
        self.general_message = [] if general_message is None else general_message
        self.response = {} if response is None else response

        if not isinstance(self.general_message, list):
            self.general_message = [self.general_message]

        self.message = {"general": self.general_message} | self.message

    def get_success_response(self) -> Response:
        """Returns a success response.

        Returns:
            Response: A success response object.
        """
        return Response(
            data={
                "hasError": False,
                "statusCode": status.HTTP_200_OK,
                "message": self.message,
                "response": self.response,
            },
            status=status.HTTP_200_OK,
        )

    def get_failure_response(
            self,
            status_code: int = 400,
            http_status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> Response:
        """Returns a failure response.

        Args:
            status_code (int, optional): A custom status code for the response.
                Defaults to 400.
            http_status_code (int, optional): An HTTP status code for the response.
                Defaults to status.HTTP_400_BAD_REQUEST.

        Returns:
            Response: A failure response object.
        """
        return Response(
            data={
                "hasError": True,
                "statusCode": status_code,
                "message": self.message,
                "response": self.response,
            },
            status=http_status_code,
        )

    def get_unauthorized_response(
            self
    ) -> Response:
        """
        Returns:
            Response: A failure response object.
        """
        return Response(
            data={
                "hasError": True,
                "statusCode": 403,
                "message": self.message,
                "response": self.response,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    def paginated_response(self, data: dict, pagination: dict) -> Response:
        """
        Generates a paginated response.

        Args:
            data (dict): The data to be included in the response.
            pagination (dict): The pagination details.

        Returns:
            Response: The generated paginated response.

        """

        self.response.update({"data": data, "pagination": pagination})
        return Response(
            data={
                "hasError": False,
                "statusCode": status.HTTP_200_OK,
                "message": self.message,
                "response": self.response,
            },
            status=status.HTTP_200_OK,
        )


class ImageResponse:
    def __init__(self, path: str):
        fs = FileSystemStorage()
        if fs.exists(path):
            self.file = fs.open(path)
        else:
            self.file = None

    def exists(self) -> bool:
        return False if self.file is None else True

    def get_success_response(self) -> Response:
        return HttpResponse(self.file, status=status.HTTP_200_OK, content_type='image/png')

    def get_failure_response(self, http_status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
        return HttpResponse(self.file, status=http_status_code, content_type='image/png')
