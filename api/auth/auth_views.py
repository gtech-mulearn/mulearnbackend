import decouple
import requests
from rest_framework.views import APIView

from utils.response import CustomResponse
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s


AUTH_DOMAIN = decouple.config("AUTH_DOMAIN")

# (connect, read) seconds. The read timeout stays 30s (logins can be slow on the
# auth server); the connect timeout stops an unreachable auth server from
# holding the request thread for the full 30s.
AUTH_PROXY_TIMEOUT = (5, 30)


def _forward_to_auth(path, payload, failure_message, success_message=None):
    """
    POST payload to the auth server and wrap its reply in a CustomResponse.

    The four proxies below used to call response.json() and trust the result:
    a non-JSON or non-dict body, or a "message" that was not a dict, raised
    and returned 500, and an error status whose body had no "hasError" key was
    returned as "Access Granted" with an empty response. Those cases now return
    failure_message. Messages for the normal cases are unchanged.
    """
    try:
        response = requests.post(
            f"{AUTH_DOMAIN}{path}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=AUTH_PROXY_TIMEOUT,
        )
        data = response.json()
    except requests.exceptions.Timeout:
        return CustomResponse(
            general_message="Authentication server timeout"
        ).get_failure_response()
    except requests.exceptions.RequestException as e:
        # Includes a body that is not JSON (requests' JSONDecodeError).
        return CustomResponse(
            general_message=f"Authentication server error: {str(e)}"
        ).get_failure_response()
    except ValueError:
        return CustomResponse(general_message=failure_message).get_failure_response()

    if not isinstance(data, dict):
        return CustomResponse(general_message=failure_message).get_failure_response()

    if data.get("hasError") or response.status_code >= 400:
        message = data.get("message")
        general = message.get("general") if isinstance(message, dict) else None
        if isinstance(general, list) and general:
            text = general[0]
        elif isinstance(general, str) and general:
            text = general
        else:
            text = failure_message
        return CustomResponse(general_message=text).get_failure_response()

    if success_message:
        return CustomResponse(
            general_message=success_message,
            response=data.get("response"),
        ).get_success_response()
    return CustomResponse(response=data.get("response")).get_success_response()


class GoogleMobileAuthProxyAPI(APIView):
    """
    Proxy endpoint for Google mobile authentication.
    Forwards requests to the auth server and returns the response.
    """

    @extend_schema(tags=['Auth'], description="Create Google Mobile Auth Proxy.",
        responses={200: inline_serializer("AuthTokenResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(default={}),
            "response": s.DictField(
                help_text="Upstream auth payload (access_token, refresh_token, user info, etc.)"
            ),
        })},
    )
    def post(self, request):
        id_token = request.data.get("id_token") or request.data.get("idToken")

        if not id_token:
            return CustomResponse(
                general_message="ID token is required"
            ).get_failure_response()

        return _forward_to_auth(
            "/api/v1/auth/google-mobile/", {"id_token": id_token}, "Authentication failed", success_message="Access Granted"
        )


class AppleMobileAuthProxyAPI(APIView):
    """
    Proxy endpoint for Apple mobile authentication.
    Forwards requests to the auth server and returns the response.
    """

    @extend_schema(tags=['Auth'], description="Create Apple Mobile Auth Proxy.",
        responses={200: inline_serializer("AuthAppleTokenResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(default={}),
            "response": s.DictField(
                help_text="Upstream auth payload (access_token, refresh_token, user info, etc.)"
            ),
        })},
    )
    def post(self, request):
        identity_token = request.data.get("identity_token") or request.data.get("identityToken")
        email = request.data.get("email")

        if not identity_token:
            return CustomResponse(
                general_message="Identity token is required"
            ).get_failure_response()

        payload = {"identity_token": identity_token}
        if email:
            payload["email"] = email

        return _forward_to_auth(
            "/api/v1/auth/apple-mobile/", payload, "Authentication failed", success_message="Access Granted"
        )


class UserAuthenticationProxyAPI(APIView):
    """
    Proxy endpoint for email/password user authentication.
    Forwards requests to the auth server and returns the response.
    """

    @extend_schema(tags=['Auth'], description="Create User Authentication Proxy.",
        responses={200: inline_serializer("AuthUserAuthResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(default={}),
            "response": s.DictField(
                help_text="Upstream auth payload (access_token, refresh_token, user info, etc.)"
            ),
        })},
    )
    def post(self, request):
        email = request.data.get("emailOrMuid")
        password = request.data.get("password")

        if not email or not password:
            return CustomResponse(
                general_message="Email and password are required"
            ).get_failure_response()

        return _forward_to_auth(
            "/api/v1/auth/user-authentication/", {"emailOrMuid": email, "password": password}, "Authentication failed", success_message="Access Granted"
        )


class RefreshTokenProxyAPI(APIView):
    """
    Proxy endpoint for token refresh.
    Forwards requests to the auth server and returns fresh tokens.
    """

    @extend_schema(tags=['Auth'], description="Create Refresh Token Proxy.",
        responses={200: inline_serializer("AuthRefreshTokenResponse", fields={
            "hasError": s.BooleanField(default=False),
            "statusCode": s.IntegerField(default=200),
            "message": s.DictField(default={}),
            "response": s.DictField(
                help_text="Upstream token payload (new access_token, refresh_token, expiry, etc.)"
            ),
        })},
    )
    def post(self, request):
        refresh_token = request.data.get("refreshToken") or request.data.get("refresh_token")

        if not refresh_token:
            return CustomResponse(
                general_message="Refresh token is required"
            ).get_failure_response()

        return _forward_to_auth(
            "/api/v1/auth/get-access-token/", {"refreshToken": refresh_token}, "Token refresh failed"
        )
