import json
import requests

from utils.response import CustomResponse
from utils.permission import JWTUtils
from db.user import User

from rest_framework.views import APIView
from django.conf import settings
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiResponse
from rest_framework import serializers as s


class WadhwaniAuthToken(APIView):
    @extend_schema(tags=['Integrations - Wadhwani'], description="Create Wadhwani Auth Token.",
        responses={200: inline_serializer(
            name='WadhwaniAuthTokenResponse',
            fields={
                'access_token': s.CharField(),
                'token_type': s.CharField(),
                'expires_in': s.IntegerField(),
                'scope': s.CharField(required=False, allow_blank=True),
            },
        )},
    )
    def post(self, request):
        url = settings.WADHWANI_CLIENT_AUTH_URL

        data = {
            "grant_type": "client_credentials",
            "client_id": "mulearn",
            "client_secret": settings.WADHWANI_CLIENT_SECRET,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = requests.post(url, data=data, headers=headers)

        if response.json().get("error", None):
            return CustomResponse(
                general_message="Invalid credentials", response=response.json()
            ).get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()


class WadhwaniUserLogin(APIView):
    @extend_schema(tags=['Integrations - Wadhwani'], description="Create Wadhwani User Login.",
        responses={200: inline_serializer(
            name='WadhwaniUserLoginResponse',
            fields={
                'status': s.CharField(),
                'accessToken': s.CharField(required=False),
                'expiresIn': s.IntegerField(required=False),
                'userCreated': s.BooleanField(required=False),
                'courseEnrolled': s.BooleanField(required=False),
                'redirectionUrl': s.CharField(required=False, allow_blank=True),
            },
        )},
    )
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/iamservice/oauth/login"
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)
        if not user.mobile:
            return CustomResponse(
                general_message="Please update your mobile number and try again."
            ).get_failure_response()
        if not (token := request.data.get("Client-Auth-Token", None)):
            return CustomResponse(
                general_message="Token is required"
            ).get_failure_response()

        if not (course_root_id := request.data.get("course_root_id", None)):
            return CustomResponse(
                general_message="Course Root ID is required"
            ).get_failure_response()

        headers = {"Content-Type": "application/json"}
        data = json.dumps(
            {
                "name": user.full_name,
                "candidateId": user.id,
                "userName": user.email,
                "email": user.email,
                "mobile": f"+91-{user.mobile}",
                "countryCode": "IN",
                "userLanguageCode": "en",
                "token": token,
                "courseRootId": course_root_id,
            }
        )
        response = requests.post(url, headers=headers, data=data)

        if response.json().get("status", None) == "ERROR":
            return CustomResponse(
                general_message="Something went wrong", response=response.json()
            ).get_failure_response()
        if response.json().get("status", None) == "FAILURE":
            return CustomResponse(
                general_message="Invalid Input", response=response.json()
            ).get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()


class WadhwaniCourseDetails(APIView):
    @extend_schema(tags=['Integrations - Wadhwani'], description="Create Wadhwani Course Details.",
        responses={200: inline_serializer(
            name='WadhwaniCourseDetailsResponse',
            fields={
                'status': s.CharField(),
                'courses': s.ListField(
                    child=inline_serializer(
                        name='WadhwaniCourseItem',
                        fields={
                            'courseRootId': s.CharField(),
                            'name': s.CharField(),
                            'description': s.CharField(required=False, allow_blank=True),
                            'thumbnailUrl': s.CharField(required=False, allow_null=True),
                        },
                    ),
                    required=False,
                ),
            },
        )},
    )
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/courseservice/oauth/client/courses"

        if not (token := request.data.get("Client-Auth-Token", None)):
            return CustomResponse(
                general_message="Token is required"
            ).get_failure_response()

        headers = {"Authorization": token}
        response = requests.get(url, headers=headers)

        if response.json().get("status", None) == "ERROR":
            return CustomResponse(
                general_message="No courses available", response=response.json()
            ).get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()


class WadhwaniCourseEnrollStatus(APIView):
    @extend_schema(tags=['Integrations - Wadhwani'], description="Create Wadhwani Course Enroll Status.",
        responses={200: inline_serializer(
            name='WadhwaniCourseEnrollStatusResponse',
            fields={
                'status': s.CharField(),
                'enrolledCourses': s.ListField(
                    child=inline_serializer(
                        name='WadhwaniEnrolledCourseItem',
                        fields={
                            'courseRootId': s.CharField(),
                            'name': s.CharField(),
                            'enrollmentDate': s.CharField(required=False, allow_null=True),
                            'completionStatus': s.CharField(required=False, allow_null=True),
                        },
                    ),
                    required=False,
                ),
            },
        )},
    )
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/courseservice/oauth/client/courses"
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)

        if not (token := request.data.get("Client-Auth-Token", None)):
            return CustomResponse(
                general_message="Token is required"
            ).get_failure_response()

        headers = {"Authorization": token}
        response = requests.get(url, params={"username": user.email}, headers=headers)

        if response.json().get("status", None) == "ERROR":
            return CustomResponse(
                general_message="User doesn't have any enrolled courses",
                response=response.json(),
            ).get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()


class WadhwaniCourseQuizData(APIView):
    @extend_schema(tags=['Integrations - Wadhwani'], description="Create Wadhwani Course Quiz Data.",
        responses={200: inline_serializer(
            name='WadhwaniCourseQuizDataResponse',
            fields={
                'status': s.CharField(),
                'quizData': s.ListField(
                    child=inline_serializer(
                        name='WadhwaniQuizItem',
                        fields={
                            'quizId': s.CharField(),
                            'quizName': s.CharField(),
                            'score': s.FloatField(required=False, allow_null=True),
                            'totalMarks': s.FloatField(required=False, allow_null=True),
                            'attemptDate': s.CharField(required=False, allow_null=True),
                        },
                    ),
                    required=False,
                ),
            },
        )},
    )
    def post(self, request):
        if not (token := request.data.get("Client-Auth-Token", None)):
            return CustomResponse(
                general_message="Token is required"
            ).get_failure_response()

        if not (course_id := request.data.get("course_id", None)):
            return CustomResponse(
                general_message="Course ID is required"
            ).get_failure_response()

        headers = {"Authorization": token}
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)
        url = (
            settings.WADHWANI_BASE_URL
            + f"/api/v1/courseservice/oauth/course/{course_id}/reports/quiz/student/{user.email}"
        )
        response = requests.get(url, headers=headers)

        if response.json().get("status", None) == "ERROR":
            return CustomResponse(
                general_message="No quiz data available", response=response.json()
            ).get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()
