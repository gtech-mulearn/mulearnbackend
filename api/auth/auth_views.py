import decouple
import requests
from rest_framework.views import APIView

from utils.response import CustomResponse
from drf_spectacular.utils import extend_schema
from utils.schema_utils import CustomResponseSerializer


AUTH_DOMAIN = decouple.config("AUTH_DOMAIN")


class GoogleMobileAuthProxyAPI(APIView):
    """
    Proxy endpoint for Google mobile authentication.
    Forwards requests to the auth server and returns the response.
    """

    @extend_schema(tags=['Auth'], description="Create Google Mobile Auth Proxy.",
        responses={200: CustomResponseSerializer},
    )
    def post(self, request):
        id_token = request.data.get("id_token") or request.data.get("idToken")

        if not id_token:
            return CustomResponse(
                general_message="ID token is required"
            ).get_failure_response()

        try:
            response = requests.post(
                f"{AUTH_DOMAIN}/api/v1/auth/google-mobile/",
                json={"id_token": id_token},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            data = response.json()

            if data.get("hasError"):
                return CustomResponse(
                    general_message=data.get("message", {}).get("general", ["Authentication failed"])[0]
                ).get_failure_response()

            return CustomResponse(
                general_message="Access Granted",
                response=data.get("response"),
            ).get_success_response()

        except requests.exceptions.Timeout:
            return CustomResponse(
                general_message="Authentication server timeout"
            ).get_failure_response()
        except requests.exceptions.RequestException as e:
            return CustomResponse(
                general_message=f"Authentication server error: {str(e)}"
            ).get_failure_response()


class AppleMobileAuthProxyAPI(APIView):
    """
    Proxy endpoint for Apple mobile authentication.
    Forwards requests to the auth server and returns the response.
    """

    @extend_schema(tags=['Auth'], description="Create Apple Mobile Auth Proxy.",
        responses={200: CustomResponseSerializer},
    )
    def post(self, request):
        identity_token = request.data.get("identity_token") or request.data.get("identityToken")
        email = request.data.get("email")

        if not identity_token:
            return CustomResponse(
                general_message="Identity token is required"
            ).get_failure_response()

        try:
            payload = {"identity_token": identity_token}
            if email:
                payload["email"] = email

            response = requests.post(
                f"{AUTH_DOMAIN}/api/v1/auth/apple-mobile/",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            data = response.json()

            if data.get("hasError"):
                return CustomResponse(
                    general_message=data.get("message", {}).get("general", ["Authentication failed"])[0]
                ).get_failure_response()

            return CustomResponse(
                general_message="Access Granted",
                response=data.get("response"),
            ).get_success_response()

        except requests.exceptions.Timeout:
            return CustomResponse(
                general_message="Authentication server timeout"
            ).get_failure_response()
        except requests.exceptions.RequestException as e:
            return CustomResponse(
                general_message=f"Authentication server error: {str(e)}"
            ).get_failure_response()


class UserAuthenticationProxyAPI(APIView):
    """
    Proxy endpoint for email/password user authentication.
    Forwards requests to the auth server and returns the response.
    """

    @extend_schema(tags=['Auth'], description="Create User Authentication Proxy.",
        responses={200: CustomResponseSerializer},
    )
    def post(self, request):
        email = request.data.get("emailOrMuid")
        password = request.data.get("password")

        if not email or not password:
            return CustomResponse(
                general_message="Email and password are required"
            ).get_failure_response()

        try:
            response = requests.post(
                f"{AUTH_DOMAIN}/api/v1/auth/user-authentication/",
                json={"emailOrMuid": email, "password": password},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            data = response.json()

            if data.get("hasError"):
                return CustomResponse(
                    general_message=data.get("message", {}).get("general", ["Authentication failed"])[0]
                ).get_failure_response()

            return CustomResponse(
                general_message="Access Granted",
                response=data.get("response"),
            ).get_success_response()

        except requests.exceptions.Timeout:
            return CustomResponse(
                general_message="Authentication server timeout"
            ).get_failure_response()
        except requests.exceptions.RequestException as e:
            return CustomResponse(
                general_message=f"Authentication server error: {str(e)}"
            ).get_failure_response()


class RefreshTokenProxyAPI(APIView):
    """
    Proxy endpoint for token refresh.
    Forwards requests to the auth server and returns fresh tokens.
    """

    @extend_schema(tags=['Auth'], description="Create Refresh Token Proxy.",
        responses={200: CustomResponseSerializer},
    )
    def post(self, request):
        refresh_token = request.data.get("refreshToken") or request.data.get("refresh_token")

        if not refresh_token:
            return CustomResponse(
                general_message="Refresh token is required"
            ).get_failure_response()

        try:
            response = requests.post(
                f"{AUTH_DOMAIN}/api/v1/auth/get-access-token/",
                json={"refreshToken": refresh_token},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )

            data = response.json()

            if data.get("hasError"):
                return CustomResponse(
                    general_message=data.get("message", {}).get("general", ["Token refresh failed"])[0]
                ).get_failure_response()

            return CustomResponse(
                response=data.get("response"),
            ).get_success_response()

        except requests.exceptions.Timeout:
            return CustomResponse(
                general_message="Authentication server timeout"
            ).get_failure_response()
        except requests.exceptions.RequestException as e:
            return CustomResponse(
                general_message=f"Authentication server error: {str(e)}"
            ).get_failure_response()
