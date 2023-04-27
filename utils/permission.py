import datetime
from datetime import datetime
from typing import List

import jwt
from django.conf import settings
from django.http import HttpRequest
from rest_framework import authentication
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from mulearnbackend.settings import SECRET_KEY
from .exception import CustomException
from .response import CustomResponse
from .types import RoleType
from .utils import DateTimeUtils


class CustomizePermission(BasePermission):
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
            CustomException: If authentication fails.
        """
        try:
            auth_header = get_authorization_header(request).decode("utf-8")
            if not auth_header or not auth_header.startswith(self.token_prefix):
                raise AuthenticationFailed("Invalid token header")

            token = auth_header[len(self.token_prefix):].strip()
            if not token:
                raise AuthenticationFailed("Empty token")

            payload = jwt.decode(
                token, self.secret_key, algorithms=["HS256"], verify=True
            )

            user_id = payload.get("id")
            expiry = datetime.strptime(
                payload.get("expiry"), "%Y-%m-%d %H:%M:%S"
            )

            if not user_id or expiry < DateTimeUtils.get_current_utc_time():
                raise AuthenticationFailed("Token expired or invalid")

            return None, payload

        except jwt.exceptions.DecodeError:
            raise AuthenticationFailed("Invalid token signature")
        except AuthenticationFailed as e:
            raise CustomException(
                {"hasError": True, "message": {"general": [str(e)]}, "statusCode": 1000}
            )
        except Exception:
            raise CustomException(
                {
                    "hasError": True,
                    "message": {"general": ["Invalid token"]},
                    "statusCode": 1000,
                }
            )


class JWTUtils:
    @staticmethod
    def fetch_role_from_jwt(request):
        token = authentication.get_authorization_header(request).decode("utf-8").split()
        payload = jwt.decode(token[1], settings.SECRET_KEY, algorithms=["HS256"], verify=True)
        roles = payload.get("roles")
        if roles is None:
            raise Exception("The corresponding JWT token does not contain the 'roles' key")
        return roles


class RoleRequired:
    """
    Class-based view that restricts access to views based on user roles.

    Usage:
    @method_decorator(RoleRequired(['admin']))
    def my_view(request, arg1, arg2):
        ...
    """

    def __init__(self, roles: List[str]):
        self.roles = roles

    def __call__(self, view_func):
        def wrapped_view_func(obj, request: HttpRequest, *args, **kwargs):
            # If a RoleType enum is provided, use its value instead
            for index, role in enumerate(self.roles):
                if isinstance(role, RoleType):
                    self.roles[index] = role.value

            # Check if the user has one of the allowed roles
            for jwt_role in JWTUtils.fetch_role_from_jwt(request):
                if jwt_role in self.roles:
                    response = view_func(obj, request, *args, **kwargs)
                    return response

            # If the user does not have the required role, return a failure response
            else:
                return CustomResponse(
                    general_message="You do not have the required role to access this page.").get_failure_response()

        return wrapped_view_func
