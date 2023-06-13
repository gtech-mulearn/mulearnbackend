from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework.views import APIView

from db.user import Role
from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.types import RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DiscordWebhooks
from . import dash_roles_serializer


class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        roles_queryset = Role.objects.all()
        queryset = CommonUtils.get_paginated_queryset(
            roles_queryset, request, ["id", "title"]
        )
        serializer = dash_roles_serializer.RoleDashboardSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value, ])
    def patch(self, request, roles_id):
        try:
            role = Role.objects.filter(id=roles_id).first()
            oldName = role.title
        except AttributeError as e:
            return CustomResponse(general_message="Role doesn't exist").get_failure_response()

        serializer = dash_roles_serializer.RoleDashboardSerializer(
            role, data=request.data, partial=True, context={"request": request}
        )

        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        try:

            serializer.save()
            newname = role.title

            DiscordWebhooks.channelsAndCategory(
                WebHookCategory.ROLE.value,
                WebHookActions.EDIT.value,
                newname,
                oldName
            )

            return CustomResponse(
                response={"data": serializer.data}
            ).get_success_response()

        except IntegrityError as e:
            return CustomResponse(
                general_message="Database integrity error",
            ).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
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

    @role_required([RoleType.ADMIN.value, ])
    def post(self, request):
        serializer = dash_roles_serializer.RoleDashboardSerializer(
            data=request.data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            DiscordWebhooks.channelsAndCategory(
                WebHookCategory.ROLE.value,
                WebHookActions.CREATE.value,
                request.data.get("title"),
            )

            return CustomResponse(
                response={"data": serializer.data}
            ).get_success_response()
        else:
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()


class RoleManagementCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        role = Role.objects.all()
        role_serializer_data = dash_roles_serializer.RoleDashboardSerializer(
            role, many=True
        ).data
        return CommonUtils.generate_csv(role_serializer_data, "Roles")
