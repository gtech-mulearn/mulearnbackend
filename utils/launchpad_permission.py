import jwt
from decouple import config
from rest_framework.permissions import BasePermission
from django.utils import timezone
from datetime import datetime
from db.launchpad import LaunchpadCompanies, LaunchpadRecruiters
from utils.response import CustomResponse
from .exception import UnauthorizedAccessException
from .response import CustomResponse

from django.conf import settings
from rest_framework import authentication
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from mulearnbackend.settings import SECRET_KEY
from utils.utils import DateTimeUtils

class LaunchpadJWTPermission(BasePermission):
    """
    Custom permission class to authenticate user based on bearer token.

    Attributes:
        token_prefix (str): The prefix of the token in the header.
        secret_key (str): The secret key to verify the token signature.
    """

    token_prefix = "Bearer"
    secret_key = SECRET_KEY

    def authenticate(self, request):
        """
        Authenticates the user based on the bearer token in the header.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            tuple: A tuple of (user, token_payload) if authentication is successful.

        Raises:
            UnauthorizedAccessException: If authentication fails.
        """
        return LaunchpadJWTUtils.is_jwt_authenticated(request)

    def authenticate_header(self, request):
        """
        Returns a string value for the WWW-Authenticate header.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            str: The value for the WWW-Authenticate header.
        """
        return f'{self.token_prefix} realm="api"'


class LaunchpadJWTUtils:
    @staticmethod
    def fetch_user_type(request):
        token = authentication.get_authorization_header(request).decode("utf-8").split()
        payload = jwt.decode(
            token[1], settings.SECRET_KEY, algorithms=["HS256"], verify=True
        )
        user_type = payload.get("user_type")
        if user_type is None:
            raise Exception(
                "The corresponding JWT token does not contain the 'user_type' key"
            )
        return user_type

    @staticmethod
    def fetch_user_id(request):
        token = authentication.get_authorization_header(request).decode("utf-8").split()
        payload = jwt.decode(
            token[1], settings.SECRET_KEY, algorithms=["HS256"], verify=True
        )
        user_id = payload.get("id")
        if user_id is None:
            raise Exception(
                "The corresponding JWT token does not contain the 'user_id' key"
            )
        return user_id

    @staticmethod
    def is_jwt_authenticated(request):
        token_prefix = "Bearer"
        secret_key = SECRET_KEY
        try:
            auth_header = get_authorization_header(request).decode("utf-8")
            if not auth_header or not auth_header.startswith(token_prefix):
                raise UnauthorizedAccessException("Invalid token header")

            token = auth_header[len(token_prefix):].strip()
            if not token:
                raise UnauthorizedAccessException("Empty Token")

            payload = jwt.decode(token, secret_key, algorithms=["HS256"], verify=True)

            user_id = payload.get("id")
            expiry = datetime.strptime(payload.get("expiry"), "%Y-%m-%d %H:%M:%S%z")

            if not user_id or expiry < DateTimeUtils.get_current_utc_time():
                raise UnauthorizedAccessException("Token Expired or Invalid")

            return None, payload
        except jwt.exceptions.InvalidSignatureError as e:
            raise UnauthorizedAccessException(
                {
                    "hasError": True,
                    "message": {"general": [str(e)]},
                    "statusCode": 1000,
                }
            ) from e
        except jwt.exceptions.DecodeError as e:
            raise UnauthorizedAccessException(
                {
                    "hasError": True,
                    "message": {"general": [str(e)]},
                    "statusCode": 1000,
                }
            ) from e
        except AuthenticationFailed as e:
            raise UnauthorizedAccessException(str(e)) from e
        except Exception as e:
            raise UnauthorizedAccessException(
                {
                    "hasError": True,
                    "message": {"general": [str(e)]},
                    "statusCode": 1000,
                }
            ) from e

    @staticmethod
    def is_logged_in(request):
        try:
            LaunchpadJWTUtils.is_jwt_authenticated(request)
            return True
        except UnauthorizedAccessException:
            return False
