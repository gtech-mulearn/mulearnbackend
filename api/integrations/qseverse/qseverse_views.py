
import requests
from django.conf import settings
from rest_framework.views import APIView
from utils.response import CustomResponse
from .serializers import IssueVCSerializer


BASE_URL = settings.QSEVERSE_BASE_URL
API_KEY = settings.QSEVERSE_API_KEY
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"ApiKey {API_KEY}"
}


class IssueVerifiableCredentialView(APIView):
    def post(self, request):
        serializer = IssueVCSerializer(data=request.data)
        if serializer.is_valid():
            payload = {
                "api_key": API_KEY,
                **serializer.validated_data,
                "send_email": True,
            }
            try:
                response = requests.post(
                    f"{BASE_URL}api/issue_vc_app",
                    json=payload,
                    headers= HEADERS,
                )
                response.raise_for_status()
                return CustomResponse(
                    response=response.json()
                ).get_success_response()
            except requests.exceptions.RequestException as e:
                return CustomResponse(
                    response={"error": str(e)}
                ).get_failure_response()
        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()


class GetAllConnectedUsersView(APIView):
    def get(self, request):
        try:
            response = requests.get(
                f"{BASE_URL}api/app/connected-users",
                headers=HEADERS,
            )
            response.raise_for_status()
            return CustomResponse(
                response=response.json()
            ).get_success_response()
        except requests.exceptions.RequestException as e:
            return CustomResponse(
                response={"error": str(e)}
            ).get_failure_response()


class GetConnectedUserView(APIView):
    def get(self, request):
        key = request.query_params.get("key")
        value = request.query_params.get("value")

        if not key or not value:
            return CustomResponse(
                response={"error": "Missing 'key' or 'value'"}
            ).get_failure_response()

        try:
            response = requests.get(
                f"{BASE_URL}api/app/connected-users/search",
                headers=HEADERS,
                params={"key": key, "value": value},
            )
            response.raise_for_status()
            data = response.json()
            matching_users = data.get("matching_users", [])
            did = matching_users[0].get("did") if matching_users else None

            return CustomResponse(
                response={"did": did}
            ).get_success_response()
        except requests.exceptions.RequestException as e:
            return CustomResponse(
                response={"error": str(e)}
            ).get_failure_response()


class GetQSCredentialsView(APIView):
    def get(self, request):
        try:
            response = requests.get(
                f"{BASE_URL}api/user/credentials",
                headers=HEADERS,
            )
            response.raise_for_status()
            return CustomResponse(
                response=response.json()
            ).get_success_response()
        except requests.exceptions.RequestException as e:
            return CustomResponse(
                response={"error": str(e)}
            ).get_failure_response()
