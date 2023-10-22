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
        return self.get_response(request)

    def log_exception(self, request, exception):
        """
        Log the exception and prints the information in CLI if DEBUG is True.

        Args:
            request: The request object.
            exception: The exception object.

        """
        error_message = (
            f"Exception Type: {type(exception).__name__}; "
            f"Exception Message: {str(exception)}; "
            f"Traceback: {traceback.format_exc()}"
        )
        logger.error(error_message)

        if settings.DEBUG:
            print(error_message)

        request_info = (
            f"Request Info: METHOD: {request.method}; \n"
            f"\tPATH: {request.path}; \n"
            f"\tDATA: {json.loads(request.body.decode('utf-8')) if hasattr(request, 'body') else 'No Data'}\n"
        )
        logger.error(request_info)

        # Print to terminal if DEBUG is True
        if settings.DEBUG:
            print(request_info)

    def process_exception(self, request, exception):
        """
        Process the exception and return a response.

        Args:
            request: The request object.
            exception: The exception object.

        Returns:
            A response object.

        """
        if isinstance(exception, CustomException):
            response = CustomResponse(
                general_message=exception.detail,
            ).get_failure_response(status_code=exception.status_code)
        else:
            self.log_exception(request, exception)
            response = CustomResponse(
                general_message="Something went wrong"
            ).get_failure_response()

        # Set the renderer and renderer context
        renderer = JSONRenderer()
        response.accepted_renderer = renderer
        response.accepted_media_type = renderer.media_type
        response.renderer_context = {
            "request": request,
            "view": None,
        }

        return response.render()
