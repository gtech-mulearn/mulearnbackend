"""Email verification endpoints (spec A §4). Thin: rules live in service.py."""
import math

from drf_spectacular.utils import extend_schema
from rest_framework import exceptions
from rest_framework.views import APIView

from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse

from . import service
from .errors import VerificationError, error_response
from .throttles import EmailCodeIPThrottle, EmailCodeVerifyIPThrottle, EmailVerificationUserThrottle

TAGS = ["Email Verification"]


class _EnvelopeMixin:
    """A throttle answers in the CustomResponse envelope, like every other error."""

    def handle_exception(self, exc):
        if isinstance(exc, exceptions.Throttled):
            return error_response("code_rate_limited", retry_after=int(math.ceil(exc.wait or 60)))
        return super().handle_exception(exc)


def _run(action, *args):
    try:
        return CustomResponse(response=action(*args)).get_success_response()
    except VerificationError as error:
        return error_response(error.code, **error.extra)


def _current_user(request):
    return User.objects.filter(id=JWTUtils.fetch_user_id(request)).first()


class SignupEmailCodeAPI(_EnvelopeMixin, APIView):
    throttle_classes = [EmailCodeIPThrottle]

    @extend_schema(tags=TAGS, description="Email a 6-digit code to an address before signup.")
    def post(self, request):
        return _run(service.send_signup_code, request.data.get("email"))


class SignupEmailCodeVerifyAPI(_EnvelopeMixin, APIView):
    throttle_classes = [EmailCodeVerifyIPThrottle]

    @extend_schema(tags=TAGS, description="Exchange a signup code for an email_verification_token.")
    def post(self, request):
        return _run(service.verify_signup_code, request.data.get("email"), request.data.get("code"))


class _AccountView(_EnvelopeMixin, APIView):
    permission_classes = [CustomizePermission]
    throttle_classes = [EmailVerificationUserThrottle]

    def with_user(self, request, action, *args):
        user = _current_user(request)
        if user is None:
            return error_response("user_not_found")
        return _run(action, user, *args)


class EmailVerificationStatusAPI(_AccountView):
    throttle_classes = []  # read-only and cheap

    @extend_schema(tags=TAGS, description="Whether the current email is verified.")
    def get(self, request):
        return self.with_user(request, service.status)


class VerifyEmailRequestAPI(_AccountView):
    @extend_schema(tags=TAGS, description="Email a code to the current address.")
    def post(self, request):
        return self.with_user(request, service.request_account_code)


class VerifyEmailConfirmAPI(_AccountView):
    @extend_schema(tags=TAGS, description="Confirm the current address with its code.")
    def post(self, request):
        return self.with_user(request, service.confirm_account_code, request.data.get("code"))


class ChangeEmailRequestAPI(_AccountView):
    @extend_schema(tags=TAGS, description="Start an email change: a code goes to the new address.")
    def post(self, request):
        return self.with_user(
            request, service.request_email_change,
            request.data.get("new_email"), request.data.get("current_password"),
        )


class ChangeEmailConfirmAPI(_AccountView):
    @extend_schema(tags=TAGS, description="Finish an email change with the code from the new address.")
    def post(self, request):
        return self.with_user(request, service.confirm_email_change, request.data.get("code"))
