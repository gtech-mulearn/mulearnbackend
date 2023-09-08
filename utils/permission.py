import datetime
from datetime import datetime

import jwt
from django.conf import settings
from django.http import HttpRequest
from rest_framework import authentication
from rest_framework.authentication import get_authorization_header
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from mulearnbackend.settings import SECRET_KEY
from utils.utils import DateTimeUtils
from .exception import CustomException
from .response import CustomResponse

from db.user import DynamicRole, DynamicUser


# def get_current_utc_time():
#     return format_time(datetime.utcnow())


def format_time(date_time):
    formatted_time = date_time.strftime("%Y-%m-%d %H:%M:%S%z")
    return datetime.strptime(formatted_time, "%Y-%m-%d %H:%M:%S%z")


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
        return JWTUtils.is_jwt_authenticated(request)

    def authenticate_header(self, request):
        """
        Returns a string value for the WWW-Authenticate header.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            str: The value for the WWW-Authenticate header.
        """
        return f'{self.token_prefix} realm="api"'


class JWTUtils:
    @staticmethod
    def fetch_role(request):
        token = authentication.get_authorization_header(request).decode("utf-8").split()
        payload = jwt.decode(
            token[1], settings.SECRET_KEY, algorithms=["HS256"], verify=True
        )
        roles = payload.get("roles")
        if roles is None:
            raise Exception(
                "The corresponding JWT token does not contain the 'roles' key"
            )
        return roles

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
    def fetch_muid(request):
        token = authentication.get_authorization_header(request).decode("utf-8").split()
        payload = jwt.decode(
            token[1], settings.SECRET_KEY, algorithms=["HS256"], verify=True
        )
        muid = payload.get("muid")
        if muid is None:
            raise Exception(
                "The corresponding JWT token does not contain the 'muid' key"
            )
        return muid

    @staticmethod
    def is_jwt_authenticated(request):
        token_prefix = "Bearer"
        secret_key = SECRET_KEY
        try:
            auth_header = get_authorization_header(request).decode("utf-8")
            if not auth_header or not auth_header.startswith(token_prefix):
                raise CustomException("Invalid token header")

            token = auth_header[len(token_prefix):].strip()
            if not token:
                raise CustomException("Empty Token")

            payload = jwt.decode(token, secret_key, algorithms=["HS256"], verify=True)

            user_id = payload.get("id")
            expiry = datetime.strptime(payload.get("expiry"), "%Y-%m-%d %H:%M:%S%z")

            if not user_id or expiry < DateTimeUtils.get_current_utc_time():
                raise CustomException("Token Expired or Invalid")

            return None, payload
        except jwt.exceptions.InvalidSignatureError as e:
            raise CustomException(
                {
                    "hasError": True,
                    "message": {"general": [str(e)]},
                    "statusCode": 1000,
                }
            ) from e
        except jwt.exceptions.DecodeError as e:
            raise CustomException(
                {
                    "hasError": True,
                    "message": {"general": [str(e)]},
                    "statusCode": 1000,
                }
            ) from e
        except AuthenticationFailed as e:
            raise CustomException(str(e)) from e
        except Exception as e:
            raise CustomException(
                {
                    "hasError": True,
                    "message": {"general": [str(e)]},
                    "statusCode": 1000,
                }
            ) from e


def role_required(roles):
    def decorator(view_func):
        def wrapped_view_func(obj, request, *args, **kwargs):
            for role in JWTUtils.fetch_role(request):
                if role in roles:
                    response = view_func(obj, request, *args, **kwargs)
                    return response
            res = CustomResponse(
                general_message="You do not have the required role to access this page."
            ).get_failure_response()
            return res

        return wrapped_view_func

    return decorator

def dynamic_role_required(type):
    def decorator(view_func):
        def wrapped_view_func(obj, request, *args, **kwargs):
            dynamic_roles = DynamicRole.objects.filter(type=type).values_list('role__title', flat=True)
            roles = set(dynamic_roles)
            for role in JWTUtils.fetch_role(request):
                if role in roles:
                    response = view_func(obj, request, *args, **kwargs)
                    return response
            dynamic_users = DynamicUser.objects.filter(type=type).values_list('user__id', flat=True)
            user = JWTUtils.fetch_user_id(request)
            if user in dynamic_users:
                response = view_func(obj, request, *args, **kwargs)
                return response
            res = CustomResponse(
                general_message="You do not have the required role to access this page."
                ).get_failure_response()
            return res
        return wrapped_view_func
    return decorator

# class RoleRequired:
#     """
#     Class-based view that restricts access to views based on user roles.
#
#     Usage:
#     @method_decorator(RoleRequired(['admin']))
#     def my_view(request, arg1, arg2):
#         ...
#     """
#
#     def __init__(self, roles: List[str]):
#         self.roles = roles
#
#     def __call__(self, view_func):
#         def wrapped_view_func(obj, request: HttpRequest, *args, **kwargs):
#             # If a RoleType enum is provided, use its value instead
#             for index, role in enumerate(self.roles):
#                 if isinstance(role, RoleType):
#                     self.roles[index] = role.value
#
#             # Check if the user has one of the allowed roles
#             for jwt_role in JWTUtils.fetch_role(request):
#                 if jwt_role in self.roles:
#                     response = view_func(obj, request, *args, **kwargs)
#                     return response
#
#             # If the user does not have the required role, return a failure response
#             return CustomResponse(
#                 general_message="You do not have the required role to access this page."
#             ).get_failure_response()
#
#         return wrapped_view_func
