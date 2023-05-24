from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

from db.user import User
from utils.permission import CustomizePermission, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from .dash_user_serializer import UserDashboardSerializer


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

        return CustomResponse(
            response={
                "users": serializer.data,
                "pagination": queryset.get("pagination"),
            }
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN])
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserDashboardSerializer(user, data=request.data, partial=True)

        if not serializer.is_valid():
            return CustomResponse(
                response={"users": serializer.errors}
            ).get_failure_response()
        try:
            serializer.save()
            return CustomResponse(
                response={"users": serializer.data}
            ).get_success_response()

        except IntegrityError as e:
            return CustomResponse(response={"users": str(e)}).get_failure_response()

    @RoleRequired(roles=[RoleType.ADMIN])
    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return CustomResponse().get_success_response()


# class UserVerificationAPI(APIView):
#     authentication_classes = [CustomizePermission]

#     @RoleRequired(roles=[RoleType.ADMIN])
#     def get(self, request):
#         user_queryset = User.objects.all()
#         queryset = CommonUtils.get_paginated_queryset(
#             user_queryset,
#             request,
#             ["first_name", "last_name", "role_title"],
#         )
#         serializer = UserVerificationSerializer(queryset.get("queryset"), many=True)

#         return CustomResponse(
#             response={
#                 "users": serializer.data,
#                 "pagination": queryset.get("pagination"),
#             }
#         ).get_success_response()

#     # @RoleRequired(roles=[RoleType.ADMIN])
#     def patch(self, request, user_id):
#         user = get_object_or_404(User, id=user_id)
#         role_id = request.data.get("roles", [])
#         admin_id = User.objects.get(id="01ccd814-a33b-4f14-86e8-01319efb9a60")
#         # admin_id = JWTUtils.fetch_user_id(request)
        
#         role = Role.objects.get(id=role_id)
#         user_role_link = UserRoleLink(verified=True)
        
#         user_role_link.save()

#         serializer = UserDashboardSerializer(user, data=request.data, partial=True)

#         if not serializer.is_valid():
#             return CustomResponse(
#                 response={"users": serializer.errors}
#             ).get_failure_response()
#         try:
#             serializer.save()
#             return CustomResponse(
#                 response={"users": serializer.data}
#             ).get_success_response()

#         except IntegrityError as e:
#             return CustomResponse(response={"users": str(e)}).get_failure_response()

#     # @RoleRequired(roles=[RoleType.ADMIN])
#     def delete(self, request, user_id):
#         user = get_object_or_404(User, id=user_id)
#         user.delete()
#         return CustomResponse().get_success_response()
