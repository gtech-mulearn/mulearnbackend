from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from rest_framework.views import APIView

from db.user import Role, User, UserRoleLink
from utils.permission import CustomizePermission, role_required
from utils.response import CustomResponse
from utils.types import RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DiscordWebhooks
from . import dash_roles_serializer


class RoleAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        roles_queryset = Role.objects.all()
        queryset = CommonUtils.get_paginated_queryset(
            roles_queryset,
            request,
            [
                "id",
                "title",
                "description",
                "updated_by__first_name",
                "updated_by__last_name",
                "created_by__first_name",
                "created_by__last_name",
            ],
            {
                "title": "title",
                "description": "description",
                "updated_by": "updated_by__first_name",
                "created_by": "created_by__first_name",
                "updated_at": "updated_at",
                "created_at": "created_at",
            },
        )
        serializer = dash_roles_serializer.RoleDashboardSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, roles_id):
        try:
            role = Role.objects.filter(id=roles_id).first()
            oldName = role.title
        except AttributeError as e:
            return CustomResponse(
                general_message="Role doesn't exist"
            ).get_failure_response()

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

            DiscordWebhooks.general_updates(
                WebHookCategory.ROLE.value, WebHookActions.EDIT.value, newname, oldName
            )

            return CustomResponse(
                response={"data": serializer.data}
            ).get_success_response()

        except IntegrityError as e:
            return CustomResponse(
                general_message="Database integrity error",
            ).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, roles_id):
        try:
            role = Role.objects.get(id=roles_id)
            role.delete()

            DiscordWebhooks.general_updates(
                WebHookCategory.ROLE.value, WebHookActions.DELETE.value, role.title
            )
            return CustomResponse(
                general_message="Role deleted successfully"
            ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        serializer = dash_roles_serializer.RoleDashboardSerializer(
            data=request.data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            DiscordWebhooks.general_updates(
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

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        role = Role.objects.all()
        role_serializer_data = dash_roles_serializer.RoleDashboardSerializer(
            role, many=True
        ).data
        return CommonUtils.generate_csv(role_serializer_data, "Roles")


class UserRoleSearchAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, role_id):
        user = User.objects.filter(user_role_link_user__role_id=role_id).distinct()
        paginated_queryset = CommonUtils.get_paginated_queryset(
            user,
            request,
            ["mu_id", "first_name", "last_name"],
            {"mu_id": "mu_id", "first_name": "first_name", "last_name": "last_name"},
        )

        serializer = dash_roles_serializer.UserRoleSearchSerializer(
            paginated_queryset.get("queryset"), many=True
        ).data

        return CustomResponse(
            response={
                "data": serializer,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class UserRole(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        try:
            serializer = dash_roles_serializer.UserRoleCreateSerializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                return CustomResponse(
                    general_message=serializer.errors
                ).get_failure_response()

            serializer.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.USER_ROLE.value,
                WebHookActions.UPDATE.value,
                request.data.get("user_id"),
            )
            return CustomResponse(
                general_message="Role Added Successfully"
            ).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request):
        try:
            serializer = dash_roles_serializer.UserRoleCreateSerializer(
                data=request.data, context={"request": request}
            )
            if not serializer.is_valid():
                return CustomResponse(
                    general_message=serializer.errors
                ).get_failure_response()

            user_id = request.data.get("user_id")
            role_id = request.data.get("role_id")
            user_role_link = UserRoleLink.objects.get(role_id=role_id, user_id=user_id)

            user_role_link.delete()

            DiscordWebhooks.general_updates(
                WebHookCategory.USER_ROLE.value,
                WebHookActions.DELETE.value,
                user_role_link.id,
            )
            return CustomResponse(
                general_message="User Role deleted successfully"
            ).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
