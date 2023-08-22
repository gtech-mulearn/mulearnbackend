from db.organization import College, Organization
from utils.types import OrganizationType
from utils.permission import JWTUtils
from utils.response import CustomResponse
from decouple import config
from rest_framework.views import APIView
from .serializer import CollegeCreateDeleteSerializer, CollegeListSerializer, CollegeEditSerializer


class CollegeApi(APIView):
    def get(self, request):
        colleges = College.objects.all()
        serializer = CollegeListSerializer(colleges, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = CollegeCreateDeleteSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Level added successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    def delete(self, request):
        if college := College.objects.filter(org_id=request.data.get('org_id')).first():
            CollegeCreateDeleteSerializer().destroy(college)
            return CustomResponse(general_message='College succesfully deleted').get_success_response()
        return CustomResponse(general_message='Invalid college').get_failure_response()

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        college = College.objects.filter(org_id=request.data.get('org_id')).first()
        serializer = CollegeEditSerializer(college, data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Level updated successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

# class CollegeDropDownApi(APIView):
#     colleges = Organization.objects.filter(type=OrganizationType.COLLEGE.value)
