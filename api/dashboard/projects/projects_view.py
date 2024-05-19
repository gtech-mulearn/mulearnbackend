from django.http import JsonResponse
from rest_framework import status
from rest_framework.views import APIView

from utils.utils import CommonUtils
from .serializer import ProjectsCUDSerializer, ProjectsSerializer
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from db.projects import Projects


class ProjectsView(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request, projects_id=None):
        if projects_id is not None:
            project = Projects.objects.filter(id=projects_id).first()
            if not project:
                return CustomResponse(
                    general_message="Invalid Project id"
                ).get_failure_response()

            serializer = ProjectsSerializer(
                project,
                many=False
            )
            return CustomResponse(
                general_message="Project Found",
                response=serializer.data
            ).get_success_response()
        
        else:
            projects = Projects.objects.all()
            paginated_queryset = CommonUtils.get_paginated_queryset(
                projects,
                request,
                ['id'],
                sort_fields={'id':'id'}
            )
            serializer = ProjectsSerializer(
                paginated_queryset.get("queryset"),
                many=True
            )
            return CustomResponse().paginated_response(
                data=serializer.data,
                pagination=paginated_queryset.get("pagination")
            )

    def post(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        serializer = ProjectsCUDSerializer(
            data=request.data,
            context={
                "user_id": user_id,
            }
        )
        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="Project created successfully",
                response=serializer.data
            ).get_success_response()

        return CustomResponse(
            general_message=serializer.errors,
        ).get_failure_response()

    def put(self, request, project_id):
        user_id = JWTUtils.fetch_user_id(request)

        project = Projects.objects.filter(id=project_id).first()

        if project is None:
            return CustomResponse(
                general_message="Invalid Project id"
            ).get_failure_response()

        serializer = ProjectsCUDSerializer(
            Projects,
            data=request.data,
            context={"user_id": user_id}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="Project edited successfully"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    def delete(self, request, project_id):
        project = Projects.objects.filter(id=project_id).first()

        if project is None:
            return CustomResponse(
                general_message="Invalid Project id"
            ).get_failure_response()

        project.delete()

        return CustomResponse(
            general_message=f"Project Deleted Successfully"
        ).get_success_response()
    
