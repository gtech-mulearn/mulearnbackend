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

        body = request._body.decode("utf-8") if hasattr(request, "_body") else "No body"
        auth = request.auth if hasattr(request, "auth") else "No Auth data"

        with suppress(json.JSONDecodeError):
            body = json.loads(body)
            body = json.dumps(body, indent=4)

        with suppress(json.JSONDecodeError):
            auth = json.dumps(auth, indent=4)
        
        exception_id = self.generate_error_id(exception)
            
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
        
    def generate_error_id(self, exception):
        error_info = f"{type(exception).__name__}: {str(exception)}"

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
