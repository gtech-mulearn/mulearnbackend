import requests

from utils.response import CustomResponse
from utils.permission import JWTUtils
from db.user import User

from rest_framework.views import APIView
from django.conf import settings

class WadhwaniAuthToken(APIView):
    def post(self, request):
        url = settings.WADHWANI_CLIENT_AUTH_URL

        data = {
            'grant_type': 'client_credentials',
            'client_id': 'mulearn',
            'client_secret': settings.WADHWANI_CLIENT_SECRET,
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(url, data=data, headers=headers)

        if response.json()["status"] == "ERROR":
            return CustomResponse(general_message="Invalid credentials").get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()
    
class WadhwaniUserLogin(APIView):
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/iamservice/oauth/login"
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)
        if not (token := request.data.get('Client-Auth-Token', None)):
            return CustomResponse(general_message="Token is required").get_failure_response()
        
        if not (course_root_id := request.data.get("course_root_id", None)):
            return CustomResponse(general_message="Course Root ID is required").get_failure_response()
        
        data = {
            "name": user.full_name,
            "candidateId": user.id,
            "userName": user.email,
            "email": user.email,
            "mobile": f"+91-{user.mobile}",
            "countryCode": "IN",
            "userLanguageCode": "en",
            "token": token,
            "courseRootId": course_root_id
        }
        response = requests.post(url, data=data)

        if response.json()["status"] == "ERROR":
            return CustomResponse(general_message="Invalid Input").get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()
    
class WadhwaniCourseDetails(APIView):
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/courseservice/oauth/client/courses"

        if not (token := request.data.get('Client-Auth-Token', None)):
            return CustomResponse(general_message="Token is required").get_failure_response()
        
        headers = {'Authorization': token}
        response = requests.get(url, headers=headers)

        if response.json()["status"] == "ERROR":
            return CustomResponse(general_message="No courses available").get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()

class WadhwaniCourseEnrollStatus(APIView):
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/courseservice/oauth/client/courses"
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)

        if not (token := request.data.get('Client-Auth-Token', None)):
            return CustomResponse(general_message="Token is required").get_failure_response()
        
        headers = {'Authorization': token}
        response = requests.get(url, params={"username": user.email}, headers=headers)

        if response.json()["status"] == "ERROR":
            return CustomResponse(general_message="User doesn't have any enrolled courses").get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()

class WadhwaniCourseQuizData(APIView):
    def post(self, request):
        if not (token := request.data.get('Client-Auth-Token', None)):
            return CustomResponse(general_message="Token is required").get_failure_response()
        
        if not (course_id := request.data.get('course_id', None)):
            return CustomResponse(general_message="Course ID is required").get_failure_response()
        
        headers = {'Authorization': token}
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)
        url = settings.WADHWANI_BASE_URL + f"/api/v1/courseservice/oauth/course/{course_id}/reports/quiz/student/{user.email}"
        response = requests.get(url, headers=headers)

        if response.json()["status"] == "ERROR":
            return CustomResponse(general_message="No quiz data available").get_failure_response()
        return CustomResponse(response=response.json()).get_success_response()