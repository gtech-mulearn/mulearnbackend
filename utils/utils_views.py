from datetime import datetime

import jwt
from rest_framework import status, authentication
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from mulearnbackend.settings import SECRET_KEY
from .exception import CustomException


class CustomResponse:
    def __init__(self, message={}, general_message=[], response={}):
        if not isinstance(general_message, list):
            general_message = [general_message]

        self.message = {"general": general_message}
        self.message.update(message)
        self.response = response

    def get_success_response(self):
        return Response(
            data={"hasError": False, "statusCode": 200,
                  "message": self.message, "response": self.response},
            status=status.HTTP_200_OK,
        )

    def get_failure_response(self, status_code=400, http_status_code=status.HTTP_400_BAD_REQUEST):
        return Response(
            data={"hasError": True, "statusCode": status_code,
                  "message": self.message, "response": self.response},
            status=http_status_code,
        )


class CustomizePermission(BasePermission):
    def authenticate(self, request):
        try:
            token = authentication.get_authorization_header(
                request).decode("utf-8").split()
            if token[0] != "Bearer" and len(token) != 2:
                exception_message = {
                    "hasError": True, "message": {"general": ["Invalid Token"]}, "statusCode": 1000}
                raise CustomException(exception_message)
            return self._authenticate_credentials(request, token[1])
        except CustomException as ce:
            raise CustomException(ce.detail)
        except Exception:
            exception_message = {"hasError": True,
                                 "message": {"general": ["Invalid token"]}, "statusCode": 1000}
            raise CustomException(exception_message)

    def _authenticate_credentials(self, request, token):
        payload = jwt.decode(token, SECRET_KEY, algorithms=[
            "HS256"], verify=True)

        id = payload.get("id", None)
        expiry = datetime.strptime(payload.get("expiry", None), "%Y-%m-%d %H:%M:%S")
        if id and expiry > get_current_utc_time():
            return None, payload

        exception_message = {"hasError": True,
                             "message": {"general": ["Token expired"]}, "statusCode": 1001}
        raise CustomException(exception_message)


def get_current_utc_time():
    return format_time(datetime.utcnow())


def format_time(date_time):
    formated_time = date_time.strftime("%Y-%m-%d %H:%M:%S")
    return datetime.strptime(formated_time, "%Y-%m-%d %H:%M:%S")


def string_to_date_time(dt_str):
    return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")


class CustomHTTPHandler:
    @staticmethod
    def get_client_ip_address(request):
        req_headers = request.META
        x_forwarded_for_value = req_headers.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for_value:
            ip_addr = x_forwarded_for_value.split(",")[-1].strip()
        else:
            ip_addr = req_headers.get("REMOTE_ADDR")
        return ip_addr
