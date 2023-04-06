from rest_framework import status, authentication
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, SAFE_METHODS
import jwt
from user.models import User
from mulearnbackend.settings import SECRET_KEY
from .exception import CustomException
from django.utils import timezone

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


class CustomizePermission(BasePermission):
    def authenticate(self, request):
        try:
            token = authentication.get_authorization_header(
                request).decode("utf-8").split()
            if token[0] != 'Bearer' and len(token) != 2:
                exception_message = {'hasError': True,
                                     'message': 'Invalid token', 'statusCode': 1000}
                raise CustomException(exception_message)
            return self._authenticate_credentials(request, token[1])
        except Exception as e:
            exception_message = {'hasError': True,
                                 'message': 'Invalid token', 'statusCode': 1000}
            raise CustomException(exception_message)

    def _authenticate_credentials(self, request, token):
        payload = jwt.decode(token, SECRET_KEY,
                             algorithms=['HS256'], verify=True)

        id = payload.get('id', None)
        expiry = payload.get('expiry', None)
        if id and expiry:
            return None, payload
        # discord_id = payload.get('id', None)
        # if discord_id:
        #     user = User.objects.filter(discord_id=discord_id)
        #     if user.exists():
        #         return user.first(), payload
        #     else:
        #         pass

        exception_message = {'hasError': True,
                             'message': 'User not found', 'statusCode': 1001}
        raise CustomException(exception_message)

def get_current_utc_time():
    return timezone.now()