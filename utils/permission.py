from functools import wraps
from db.user import UserMentor
from utils.response import CustomResponse
import datetime
from datetime import datetime

from django.conf import settings
from django.http import HttpRequest
from rest_framework import authentication
from rest_framework.authentication import get_authorization_header
from rest_framework.permissions import BasePermission

from mulearnbackend.settings import SECRET_KEY
import logging

from utils.token_verification import (
    FORMAT_LEGACY,
    FORMAT_OIDC,
    TokenError,
    _JWKSCache,
    normalise,
    token_format,
    verify_legacy_token,
    verify_oidc_token,
)
from utils.utils import DateTimeUtils

# Dedicated logger so the per-format counter can be scraped or shipped without
# wading through the rest of this service's logging.
token_logger = logging.getLogger("mulearn.token_format")

_JWKS_SINGLETON = None


def _jwks_cache():
    """
    One JWKS cache for the process.

    Built lazily rather than at import time so that this module stays
    importable when the identity provider is not configured yet - which is the
    case in every environment until authserver is deployed.
    """
    global _JWKS_SINGLETON
    if _JWKS_SINGLETON is None:
        issuer = getattr(settings, "OIDC_ISSUER", "").rstrip("/")
        _JWKS_SINGLETON = _JWKSCache(f"{issuer}/oauth/.well-known/jwks.json")
    return _JWKS_SINGLETON
from .exception import UnauthorizedAccessException
from .response import CustomResponse

from db.user import DynamicRole, DynamicUser
from utils.types import RoleType


def mentor_active_required(func):
    @wraps(func)
    def wrapper(self, request, *args, **kwargs):
        user_id = JWTUtils.fetch_user_id(request)
        if not UserMentor.objects.filter(user_id=user_id, is_active=True).exists():
            return CustomResponse(
                general_message="Your mentor account is deactivated. Please contact an administrator."
            ).get_failure_response(status_code=403)
        return func(self, request, *args, **kwargs)
    return wrapper

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

    def has_permission(self, request, view):
        try:
            JWTUtils.is_jwt_authenticated(request)
            return True
        except UnauthorizedAccessException as e:
            raise e
        except Exception as e:
            raise UnauthorizedAccessException(str(e))

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


class OptionalAuthentication(authentication.BaseAuthentication):
    """
    Authentication class for endpoints that should serve both authenticated
    and unauthenticated users. Unlike CustomizePermission, a missing
    Authorization header is treated as an anonymous request instead of
    being rejected. A token that IS present must still be valid.

    Use this in `authentication_classes` (with no `permission_classes` /
    `role_required`) on any view that wants to branch its own behavior via
    `JWTUtils.is_logged_in(request)` rather than requiring auth outright.
    """

    token_prefix = "Bearer"
    secret_key = SECRET_KEY

    def authenticate(self, request):
        auth_header = get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None
        return JWTUtils.is_jwt_authenticated(request)

    def authenticate_header(self, request):
        return f'{self.token_prefix} realm="api"'


class JWTUtils:
    """
    Claim access for authenticated requests.

    Verification happens ONCE per request, in _validated(), and every accessor
    below reads that single validated payload. Previously fetch_role,
    fetch_user_id and fetch_muid each decoded the token themselves and none of
    them checked expiry - so a caller reaching for a claim directly accepted
    expired tokens (audit finding F10).

    Both token formats are accepted during the transition. The public signatures
    are unchanged, so the ~580 call sites need no edits.
    """

    _CACHE_ATTR = "_mulearn_validated_token"

    @staticmethod
    def _raw_token(request):
        header = authentication.get_authorization_header(request).decode("utf-8")
        parts = header.split()
        if len(parts) != 2:
            raise UnauthorizedAccessException("Invalid token header")
        return parts[1]

    @staticmethod
    def _validated(request):
        """
        The verified, normalised payload for this request.

        Cached on the request object: a single request can touch several
        accessors, and re-verifying (which may consult JWKS) per accessor would
        be both slow and the very thing that let F10 happen.
        """
        cached = getattr(request, JWTUtils._CACHE_ATTR, None)
        if cached is not None:
            return cached

        token = JWTUtils._raw_token(request)
        fmt = token_format(token)

        try:
            if fmt == FORMAT_OIDC:
                payload = verify_oidc_token(
                    token,
                    jwks_cache=_jwks_cache(),
                    issuer=getattr(settings, "OIDC_ISSUER", None),
                    audience=getattr(settings, "OIDC_AUDIENCE", "mulearn-api"),
                )
            elif fmt == FORMAT_LEGACY:
                payload = verify_legacy_token(
                    token, secret=SECRET_KEY, now=DateTimeUtils.get_current_utc_time()
                )
            else:
                raise TokenError("Unsupported token algorithm")
        except TokenError as exc:
            raise UnauthorizedAccessException(str(exc)) from exc

        validated = normalise(payload, fmt)

        # Per-format counter. Legacy support is removed only when this shows
        # zero legacy validations for seven consecutive days - observed, not
        # assumed - so the counter is a precondition for that step, not
        # decoration.
        token_logger.info("token_validated format=%s", validated["format"])

        setattr(request, JWTUtils._CACHE_ATTR, validated)
        return validated

    @staticmethod
    def fetch_role(request):
        """
        Role titles for the caller.

        New-format tokens carry no roles: they are muLearn's data, not identity
        data, so they are resolved here from this service's own tables. That is
        what makes a revoked role take effect immediately rather than whenever
        the token happens to expire.
        """
        validated = JWTUtils._validated(request)
        if validated["roles"] is not None:
            return validated["roles"]

        from db.user import UserRoleLink

        return list(
            UserRoleLink.objects.filter(
                user_id=validated["user_id"]
            ).values_list("role__title", flat=True)
        )

    @staticmethod
    def fetch_user_id(request):
        user_id = JWTUtils._validated(request)["user_id"]
        if not user_id:
            raise UnauthorizedAccessException("Token has no subject")
        return user_id

    @staticmethod
    def fetch_muid(request):
        """muid is a muLearn handle, absent from new-format tokens by design."""
        validated = JWTUtils._validated(request)
        if validated["muid"] is not None:
            return validated["muid"]

        from db.user import User

        return (
            User.objects.filter(id=validated["user_id"])
            .values_list("muid", flat=True)
            .first()
        )

    @staticmethod
    def is_jwt_authenticated(request):
        validated = JWTUtils._validated(request)
        return None, validated["raw"]

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
            res = CustomResponse().get_unauthorized_response()
            return res

        return wrapped_view_func

    return decorator


class RoleRequired:
    """
    Class-based view that restricts access to views based on user roles.

    Usage:
    @method_decorator(RoleRequired([RoleType.ADMIN.value]))
    def my_view(request, arg1, arg2):
        ...
    """

    def __init__(self, roles: list):
        self.roles = roles

    def __call__(self, view_func):
        def wrapped_view_func(obj, request: HttpRequest, *args, **kwargs):
            # If a RoleType enum is provided, use its value instead
            for index, role in enumerate(self.roles):
                if isinstance(role, RoleType):
                    self.roles[index] = role.value

            # Check if the user has one of the allowed roles
            for jwt_role in JWTUtils.fetch_role(request):
                if jwt_role in self.roles:
                    response = view_func(obj, request, *args, **kwargs)
                    return response

            # If the user does not have the required role, return a failure response
            return CustomResponse(
                general_message="You do not have the required role to access this page."
            ).get_failure_response()

        return wrapped_view_func


class BackendApiKeyPermission(BasePermission):
    """
    Check for BACKEND_API_KEY in the headers.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get("Api-Key")
        return api_key == settings.BACKEND_API_KEY
