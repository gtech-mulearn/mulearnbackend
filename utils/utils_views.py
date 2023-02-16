from rest_framework.response import Response
from rest_framework import status


class CustomResponse:
    def __init__(self, has_error=False, status_code=200, message="", response={}):
        self.has_error = has_error
        self.status_code = status_code
        self.message = message
        self.response = response

    def get_success_response(self, http_status_code=status.HTTP_200_OK):
        return Response(
            data={
                "hasError": self.has_error,
                "statusCode": self.status_code,
                "message": self.message,
                "response": self.response
            }, status=http_status_code)

    def get_failure_response(self, http_status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            data={
                "hasError": self.has_error,
                "statusCode": self.status_code,
                "message": self.message,
                "response": self.response
            }, status=http_status_code)
