from rest_framework.views import APIView
from utils.permission import CustomizePermission, JWTUtils
from utils.permission import role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .projects_serializer import ProjectsListSerializer
from db.projects import Projects

class ProjectsCRUDAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        projects = Projects.objects.all()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            projects,
            request,
            ['id'],
            sort_fields = {'id':'id'}
        )

        serializer = ProjectsListSerializer(
            paginated_queryset.get("queryset"),
            many=True
        )

        return CustomResponse().paginated_response(
            data = serializer.data,
            pagination = paginated_queryset.get(
                "pagination"
            )
        )


    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = ProjectsListSerializer(
            data = request.data,
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"Project {request.data.get('project_name')} created successfully",
                response=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()


    def put(self, request,project_id):
        user_id = JWTUtils.fetch_user_id(request)

        project = Projects.objects.filter(id=project_id).first()

        if project is None:
            return CustomResponse(
                general_message="Invalid Project id"
            ).get_failure_response()

        serializer = ProjectsListSerializer(
            project,
            data=request.data,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message=f"{project.project_name} Edited Successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()


    def delete(self, request, project_id):
        project = Projects.objects.filter(id=project_id).first()

        if project is None:
            return CustomResponse(
                general_message="Invalid project id"
            ).get_failure_response()

        project.delete()

        return CustomResponse(
            general_message=f"{project.project_name} Deleted Successfully"
        ).get_success_response()
