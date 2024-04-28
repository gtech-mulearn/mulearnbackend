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
        return CustomResponse(response=response.json()).get_success_response()
    
class WadhwaniUserLogin(APIView):
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/iamservice/oauth/login"
        token = request.data.get('Client-Auth-Token', None)
        course_root_id = request.data.get("course_root_id", None)
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)
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
        return CustomResponse(response=response.json()).get_success_response()
    
class WadhwaniCourseDetails(APIView):
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/courseservice/oauth/client/courses"
        token = request.data.get('Client-Auth-Token', None)
        headers = {'Authorization': token}
        response = requests.get(url, headers=headers)
        return CustomResponse(response=response.json()).get_success_response()

class WadhwaniCourseEnrollStatus(APIView):
    def post(self, request):
        url = settings.WADHWANI_BASE_URL + "/api/v1/courseservice/oauth/client/courses"
        token = request.data.get('Client-Auth-Token', None)
        headers = {'Authorization': token}
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)
        if response.json()["status"] == "ERROR":
            return CustomResponse(general_message="User doesn't have any enrolled courses").get_failure_response()
        response = requests.get(url, params={"username": user.email}, headers=headers)
        return CustomResponse(response=response.json()).get_success_response()

class WadhwaniCourseQuizData(APIView):
    def post(self, request):
        token = request.data.get('Client-Auth-Token', None)
        course_id = request.data.get('course_id', None)
        headers = {'Authorization': token}
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)
        url = settings.WADHWANI_BASE_URL + f"/api/v1/courseservice/oauth/course/{course_id}/reports/quiz/student/{user.email}"
        response = requests.get(url, headers=headers)
        return CustomResponse(response=response.json()).get_success_response()