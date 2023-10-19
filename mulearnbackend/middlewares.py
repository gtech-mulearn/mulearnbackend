import hmac
import logging

import decouple
from django.http import JsonResponse
from rest_framework import status
from rest_framework.renderers import JSONRenderer

from utils.response import CustomResponse
from utils.utils import _CustomHTTPHandler

logger = logging.getLogger('django')


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
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.error(str(exception))
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
