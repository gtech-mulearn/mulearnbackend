from contextlib import suppress
import hashlib
import hmac
import json
import json
import logging
import traceback

import decouple
from django.conf import settings
from django.http import JsonResponse
from rest_framework import status
from rest_framework.renderers import JSONRenderer

from utils.exception import CustomException
from utils.response import CustomResponse
from utils.utils import _CustomHTTPHandler

logger = logging.getLogger("django")


class IpBindingMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.META.get("PATH_INFO").split("/")[-1]
        if path == "discord-id":
            client_ip = _CustomHTTPHandler().get_client_ip_address(request)
            arron_ip = decouple.config("AARON_CHETTAN_IP")

            if client_ip != arron_ip:
                return JsonResponse(
                    {
                        "hasError": True,
                        "statusCode": status.HTTP_401_UNAUTHORIZED,
                        "message": "Ip not verified",
                        "response": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )

        return self.get_response(request)


class ApiSignatureMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        api_path = "/".join(request.META.get("PATH_INFO").split("/")[-3:-1])
        if api_path == "lc/user-validation":
            signature = request.META.get("HTTP_SIGNATURE")
            timestamp = request.META.get("HTTP_TIMESTAMP")
            host = request.META.get("HTTP_HOST")
            request_path = request.META.get("PATH_INFO")
            request_method = request.META.get("REQUEST_METHOD")
            key = f"{request_path}::{request_method}::{timestamp}"
            new_signature = hmac.new(
                key=decouple.config("SECRET_KEY").encode(),
                msg=key.encode(),
                digestmod="SHA256",
            ).hexdigest()
            print(new_signature)
            if new_signature != signature:
                return JsonResponse(
                    {
                        "hasError": True,
                        "statusCode": status.HTTP_401_UNAUTHORIZED,
                        "message": "Signature not verified",
                        "response": {},
                    },
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        return self.get_response(request)


class UniversalErrorHandlerMiddleware:
    """
    Middleware for handling exceptions and generating error responses.

    Args:
        get_response: The callable that takes a request and returns a response.

    Methods:
        __call__(self, request): Process the request and return the response.
        log_exception(self, request, exception): Log the exception and request information.
        process_exception(self, request, exception): Process the exception and return a response.

    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Cache the body
        _ = request.body
        return self.get_response(request)

    def log_exception(self, request, exception):
        """
        Log the exception and prints the information in CLI.

        Args:
            request: The request object.
            exception: The exception object.

        """

        body = request._body.decode("utf-8", errors="replace") if hasattr(request, "_body") else "No body"
        auth = request.auth if hasattr(request, "auth") else "No Auth data"

        with suppress(json.JSONDecodeError):
            body = json.loads(body)
            body = json.dumps(body, indent=4)

        with suppress(json.JSONDecodeError):
            auth = json.dumps(auth, indent=4)

        exception_id = self.generate_error_id(exception, request)

        request_info = (
            f"EXCEPTION INFO:\n"
            f"ID: {exception_id}\n"
            f"TYPE: {type(exception).__name__}\n"
            f"MESSAGE: {str(exception)}\n"
            f"METHOD: {request.method}\n"
            f"PATH: {request.path}\n"
            f"AUTH: \n{auth}\n"
            f"BODY: \n{body}\n"
            f"TRACEBACK: {traceback.format_exc()}"
        )
        logger.error(request_info)

        print(request_info)

    def generate_error_id(self, exception, request):
        error_info = f"{type(exception).__name__}: {str(exception)}: {request.method}: {request.path}"

        hash_object = hashlib.sha256(error_info.encode())
        return hash_object.hexdigest()

    def process_exception(self, request, exception):
        """
        Process the exception and return a response.

        Args:
            request: The request object.
            exception: The exception object.

        Returns:
            A response object.

        """
        self.log_exception(request, exception)
        raise exception


class AuthContextMiddleware:
    """
    Middleware to resolve and attach AuthContext to the request.
    This runs after standard authentication (if any) or can decode the JWT itself.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from utils.permission import JWTUtils
        from utils.authorization import build_auth_context
        from db.user import User
        
        request.auth_context = None
        try:
            # Attempt to fetch user_id from JWT if present
            user_id = JWTUtils.fetch_user_id(request)
            if user_id:
                # Optimized query to fetch user with all related roles and orgs
                user = User.objects.prefetch_related(
                    'user_mentor_user', 
                    'user_role_link_user__role',
                    'user_organization_link_user__org'
                ).get(id=user_id)
                request.auth_context = build_auth_context(user)
        except Exception:
            # If no token, invalid token, or user not found, just proceed without auth_context
            pass

        return self.get_response(request)

