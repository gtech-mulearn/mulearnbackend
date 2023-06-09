
from rest_framework.views import APIView
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError

from db.user import Role
from utils.permission import CustomizePermission, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DiscordWebhooks
from .dash_roles_serializer import RoleDashboardSerializer
from . import dash_roles_serializer


class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def get(self, request):
        roles_queryset = Role.objects.all()
        queryset = CommonUtils.get_paginated_queryset(roles_queryset, request, ["id", "title"])
        serializer = RoleDashboardSerializer(queryset.get("queryset"), many=True)

        return CustomResponse().paginated_response(data=serializer.data, pagination=queryset.get("pagination"))

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def patch(self, request, roles_id):

        try:
            role = Role.objects.filter(id=roles_id).first()
        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
        
        oldName = role.title
        
        serializer = dash_roles_serializer.RoleDashboardSerializer(
            role, data=request.data, partial=True, context={'request': request}
        )
        
        DiscordWebhooks.channelsAndCategory(
            WebHookCategory.ROLE.value,
            WebHookActions.EDIT.value,
            role.title,
            oldName
        )

        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        try:
            serializer.save()
            return CustomResponse(
                response={"roles": serializer.data}
            ).get_success_response()
            
        except IntegrityError as e:
            return CustomResponse(
                general_message="Database integrity error",
            ).get_failure_response()
    

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def delete(self, request, roles_id):
        try:
            role = Role.objects.get(id=roles_id)
            role.delete()
            
            DiscordWebhooks.channelsAndCategory(
                WebHookCategory.ROLE.value,
                WebHookActions.DELETE.value,
                role.title
            )
            return CustomResponse(
                    general_message=["Role deleted successfully"]
                ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
        
        
    @RoleRequired(roles=[RoleType.ADMIN, ])
    def post(self, request):
        serializer = RoleDashboardSerializer(data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
        
            DiscordWebhooks.channelsAndCategory(
                WebHookCategory.ROLE.value,
                WebHookActions.CREATE.value,
                request.data.get('title')
            )
            
            return CustomResponse(response={"roles": serializer.data}).get_success_response()
        else:
            return CustomResponse(general_message=serializer.errors).get_failure_response()


        
class RoleManagementCSV(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN,])
    def get(self, request):
        role = Role.objects.all()
        role_serializer_data = RoleDashboardSerializer(role, many=True).data
        return CommonUtils.generate_csv(role_serializer_data, "Role")