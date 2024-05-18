from rest_framework.views import APIView

from utils.response import CustomResponse
from utils.permission import CustomizePermission, JWTUtils
from db.projects import (
    Project,
    ProjectImage,
    Comment,
    Vote
)
from db.user import User
from .projects_serializer import (
    ProjectSerializer,
    ProjectUpdateSerializer,
    CommentSerializer,
    VoteSerializer
)


class ProjectDetailAPIView(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request, pk=None):
        if pk is not None:
            project = Project.objects.get(id=pk)
            serializer = ProjectSerializer(project)
            return CustomResponse(
                response={"Project": serializer.data}
            ).get_success_response()
        else:
            return CustomResponse(
                general_message="no Project id provided"
            ).get_failure_response()
            
    def put(self, request, pk=None):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        if pk is None:
            return CustomResponse(
                general_message="no Project id provided"
            ).get_failure_response()
        project = Project.objects.get(id=pk)
        images_data = request.FILES.getlist('images')
        serializer = ProjectUpdateSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by = user)
            if images_data:
                ProjectImage.objects.filter(project=project).delete()
                for image_data in images_data:
                    ProjectImage.objects.create(project=project, image=image_data)
            read_serializer = ProjectSerializer(serializer.instance)
            return CustomResponse(
                response={"Project": read_serializer.data}
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    def delete(self, request, pk=None):
        if pk is not None:
            try:
                project = Project.objects.get(id=pk)
                project.delete()
                return CustomResponse(
                    general_message="Project deleted successfully"
                ).get_success_response()
            except Project.DoesNotExist:
                return CustomResponse(
                    general_message="Project not found"
                ).get_failure_response()
        else:
            return CustomResponse(
                general_message="no Project id provided"
            ).get_failure_response()


class ProjectsAPIView(APIView):
    authentication_classes = [CustomizePermission]
    def get(self, request):
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True)
        return CustomResponse(
            response={"Projects": serializer.data}
        ).get_success_response()
        
    def post(self, request):
        user = User.objects.get(id=JWTUtils.fetch_user_id(request))
        images_data = request.FILES.getlist('images')
        data = request.data.copy()
        if 'images' in data:
            del data['images']
        serializer = ProjectUpdateSerializer(data=data)
        if serializer.is_valid():
            project = serializer.save(created_by=user, updated_by=user)
            if images_data:
                for image_data in images_data:
                    ProjectImage.objects.create(project=project, image=image_data)
                
            read_serializer = ProjectSerializer(project)
            return CustomResponse(
                response={"Project": read_serializer.data}
            ).get_success_response()
        else:
            print(serializer.errors)
            return CustomResponse(general_message=serializer.errors).get_failure_response()

    
class ProjectVoteAPI(APIView):
        

    def post(self, request):
        serializer = VoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                response={"Vote": serializer.data}
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()
    
    def put(self, request,pk):
        vote = Vote.objects.get(id=pk)
        serializer = VoteSerializer(vote, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                response={"Vote": serializer.data}
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()
    
    def delete(self, request,pk):
        try:
            vote = Vote.objects.get(id=pk)
            vote.delete()
            return CustomResponse(
                general_message="Vote deleted successfully"
            ).get_success_response()
        except Vote.DoesNotExist:
            return CustomResponse(
                general_message="vote not found"
            ).get_failure_response()


class ProjectCommentAPI(APIView):
        
    
    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                response={"Comment": serializer.data}
            ).get_success_response()
        return CustomResponse(general_message=serializer.errors).get_failure_response()

    def put(self, request,pk):
        comment = Comment.objects.get(id=pk)
        serializer = CommentSerializer(comment, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                response={"Comment": serializer.data}
            ).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    def delete(self, request, pk):
        try:
            comment = Comment.objects.get(id=pk)
            comment.delete()
            return CustomResponse(
                general_message="comment deleted successfully"
            ).get_success_response()
        except Comment.DoesNotExist:
            return CustomResponse(
                general_message="comment not found"
            ).get_failure_response()