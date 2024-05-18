from rest_framework.views import APIView
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .serializers import ProjectRetrieveSerializer,ProjectCUDSerializer,ProjectCommandLinkRetrieveSerializer,ProjectCommandLinkCUDSerializer
from db.projects import Project,ProjectCommandLink,ProjectVote


class ProjectCRUDAPI(APIView):
    authentication_classes = [CustomizePermission]
    
    def get(self,request):
        projects = Project.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
                projects,
                request,
                ['id'],
                sort_fields={'id':'id'}
            )
        
        serializer = ProjectRetrieveSerializer(paginated_queryset.get("queryset"),many=True)
        
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination")
        )
    
    def post(self,request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = ProjectCUDSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            
            return CustomResponse(
                general_message=f"Project created successfully",
            ).get_success_response()
            
        return CustomResponse(general_message=serializer.errors).get_failure_response()
    
    def put(self,request,project_id):
        user_id = JWTUtils.fetch_user_id(request)
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return CustomResponse(general_message="Invalid Project id").get_failure_response()
        
        serializer = ProjectCUDSerializer(
            project, data=request.data, partial=True, context={'user_id': user_id}
        )
        
        if serializer.is_valid():
            serializer.save()

            return CustomResponse(general_message=f"Project edited successfully").get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()
    
    def delete(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return CustomResponse(general_message="Invalid Project id").get_failure_response()

        project.delete()

        return CustomResponse(general_message=f"Project deleted Successfully").get_success_response()