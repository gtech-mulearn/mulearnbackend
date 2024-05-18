from rest_framework.views import APIView
from db.projects import Project, ProjectUpvote
from .projects_serializer import ProjectListSerializer, ProjectSerializer
from utils.response import CustomResponse
from utils.permission import JWTUtils, CustomizePermission
from rest_framework.serializers import ValidationError

class ProjectView(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request, project_id=None):
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                return CustomResponse(general_message="Project not found!").get_failure_response()
            serializer = ProjectListSerializer(project)
            return CustomResponse(response=serializer.data).get_success_response()
        projects = Project.objects.prefetch_related('project_contributor').all()
        serializer = ProjectListSerializer(projects, many=True)
        return CustomResponse(response=serializer.data).get_success_response()
    
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        members = request.data.get('members')
        serializer = ProjectSerializer(data=request.data, context={'user_id': user_id, 'members': members})
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        try:
            serializer.save()
        except ValidationError as e:
            return CustomResponse(general_message="Invalid member id").get_failure_response()
        return CustomResponse(general_message="Project created successfully").get_success_response()
    
    def delete(self, request, id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if id is None:
            return CustomResponse(general_message="Project id is required!").get_failure_response()
        try:
            project = Project.objects.get(id=id, created_by=user_id)
        except Project.DoesNotExist:
            return CustomResponse(general_message="Project does not exists or you are not authorized to delete this project").get_failure_response()
        project.delete()
        return CustomResponse(general_message="Project Deleted successfully").get_success_response()


    def put(self, request, id=None):
        if id is None:
            return CustomResponse(general_message="Project id is required!").get_failure_response()
        try:
            instance = Project.objects.get(id=id)
        except Project.DoesNotExist:
            return CustomResponse(general_message="Project not found!").get_failure_response()
        user_id = JWTUtils.fetch_user_id(request)
        serializer = ProjectSerializer(instance=instance, data=request.data, context={"user_id": user_id})
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()
        serializer.save()
        return CustomResponse(general_message="Project edited successfully").get_success_response()

class GetUserProjectView(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        projects = Project.objects.prefetch_related("project_contributor").filter(created_by=user_id)
        serializer = ProjectListSerializer(projects, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class AddProjectUpvoteView(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request, project_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if project_id is None:
            return CustomResponse(general_message="Project id is required!").get_failure_response()
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return CustomResponse(general_message="Project does not exits!").get_failure_response()
        if project.project_upvote.filter(user_id=user_id).exists():
            return CustomResponse(general_message="You have already upvoted this project").get_failure_response()
        project.project_upvote.create(user_id=user_id)
        return CustomResponse(general_message="Successfully upvoted").get_success_response()
    
    def delete(self, request, project_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if project_id is None:
            return CustomResponse(general_message="Project id is required!").get_failure_response()
        try:
            upvote = ProjectUpvote.objects.get(project=project_id, user=user_id)
        except ProjectUpvote.DoesNotExist:
            return CustomResponse(general_message="You have not upvoted this project!").get_failure_response()
        upvote.delete()
        return CustomResponse(general_message="Successfully removed the upvote").get_success_response()