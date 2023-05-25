from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.views import APIView
from .dash_user_serializer import UserDashboardSerializer, UserVerificationSerializer

from db.user import User, UserRoleLink
from utils.permission import CustomizePermission, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN])
    def get(self, request):
        user_queryset = User.objects.all()
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["mu_id", "first_name", "last_name", "email", "mobile"],
        )
        serializer = UserDashboardSerializer(queryset.get("queryset"), many=True)
        
        return CustomResponse().paginated_response(data=serializer.data,
                                                   pagination=queryset.get('pagination'))



    @RoleRequired(roles=[RoleType.ADMIN])
    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

        serializer = UserDashboardSerializer(user, data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()

        try:
            serializer.save()
            return CustomResponse(
                response={"users": serializer.data}
            ).get_success_response()
        except IntegrityError as e:
            return CustomResponse(
                general_message="Database integrity error",
            ).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN])
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return CustomResponse(
                general_message=["User deleted successfully"]
            ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class UserManagementCSV(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN, ])
    def get(self, request):
        user = User.objects.all()
        user_serializer_data = UserDashboardSerializer(user, many=True).data
        return CommonUtils.generate_csv(user_serializer_data, "User")


class UserVerificationAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired(roles=[RoleType.ADMIN])
    def get(self, request):
        user_queryset = UserRoleLink.objects.filter(verified=False)
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["first_name", "last_name", "role_title"],
        )
        serializer = UserVerificationSerializer(queryset.get("queryset"), many=True)

        return CustomResponse().paginated_response(data=serializer.data,
                                                   pagination=queryset.get('pagination'))

    @RoleRequired(roles=[RoleType.ADMIN])
    def patch(self, request, link_id):
        try:
            user = UserRoleLink.objects.get(id=link_id)
        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

        serializer = UserVerificationSerializer(user, data=request.data, partial=True)

        if not serializer.is_valid():
            return CustomResponse(
                response={"user_role_link": serializer.errors}
            ).get_failure_response()
        try:
            serializer.save()
            return CustomResponse(
                response={"user_role_link": serializer.data}
            ).get_success_response()

        except IntegrityError as e:
            return CustomResponse(
                response={"user_role_link": str(e)}
            ).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN])
    def delete(self, request, link_id):
        try:
            link = UserRoleLink.objects.get(id=link_id)
            link.delete()
            return CustomResponse(
                general_message=["Link deleted successfully"]
            ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()
