from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from .projects_serializer import ProjectSerializer
from db.projects import Project
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse


class ProjectListView(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, *args, **kwargs):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        project_id = kwargs.get('project_id')

        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()
        
        if project_id:
            project = get_object_or_404(Project, id = project_id)
            if not project:
                return Response(
                    {"message": "No projects found."},
                    status=status.HTTP_404_NOT_FOUND
                )
        
            serializer = ProjectSerializer(project, many=False)
            return Response(serializer.data, status=status.HTTP_200_OK)

        
        projects = Project.objects.all()
        if not projects:
            return Response(
                {"message": "No projects found."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ProjectCreateView(APIView):
    authentication_classes = [CustomizePermission]
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()

        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()
        
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by = user.full_name, updated_by = user.full_name)
            return Response({"message": "Project created successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ProjectUpdateView(APIView):
    authentication_classes = [CustomizePermission]
    def put(self, request, *args, **kwargs):
        project_id = kwargs.get('project_id')
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()

        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()
        
        project = Project.objects.filter(id=project_id, created_by = user.full_name).first()
        if not project:
            return Response(
                {"general_message": "Project Not Found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ProjectSerializer(project, data=request.data)
        if serializer.is_valid():
            serializer.save(updated_by=user.full_name)
            return Response({"message": "Project updated successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ProjectDeleteView(APIView):
    authentication_classes = [CustomizePermission]
    
    def delete(self, request, project_id):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()

        if not user:
            return Response(
                {"general_message": "User Not Exists"},
                status=status.HTTP_404_NOT_FOUND
            )

        project = Project.objects.filter(id=project_id, created_by=user.full_name).first()
        if not project:
            return Response(
                {"general_message": "Project Not Found"},
                status=status.HTTP_404_NOT_FOUND
            )
        project.delete()
        return Response({"message": "Project deleted successfully"})