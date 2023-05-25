import contextlib
import uuid
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView

import decouple
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db.models import Q
from db.user import ForgotPassword, User, UserRoleLink, Role
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils, DateTimeUtils
from . import dash_user_serializer

class UserInfoAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_muid = JWTUtils.fetch_muid(request)
        user = User.objects.filter(mu_id=user_muid).first()

        if user is None:
            return CustomResponse(general_message='No user data available').get_failure_response()

        response = dash_user_serializer.UserSerializer(user, many=False).data
        return CustomResponse(response=response).get_success_response()


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
        serializer = dash_user_serializer.UserDashboardSerializer(queryset.get("queryset"), many=True)

        return CustomResponse(
            response={
                "users": serializer.data,
                "pagination": queryset.get("pagination"),
            }
        ).get_success_response()

    @RoleRequired(roles=[RoleType.ADMIN])
    def patch(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        roles = request.data.get("roles", [])
        admin_id = JWTUtils.fetch_user_id(request)

        UserRoleLink.objects.filter(user=user).delete()

        for role_title in roles:
            with contextlib.suppress(Role.DoesNotExist):
                role = Role.objects.get(title=role_title)
                user_role_link = UserRoleLink.objects.create(
                    id=uuid.uuid4(),
                    user=user,
                    role=role,
                    verified=True,
                    created_by=admin_id,
                    created_at=DateTimeUtils.get_current_utc_time(),
                )
                user_role_link.save()

        serializer = dash_user_serializer.UserDashboardSerializer(user, data=request.data, partial=True)

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

class ForgotPasswordAPI(APIView):
    def post(self, request):
        email_muid = request.data.get('emailOrMuid')
        user = User.objects.filter(
            Q(mu_id=email_muid) | Q(email=email_muid)).first()
        if user:
            created_at = DateTimeUtils.get_current_utc_time()
            expiry = created_at + timedelta(seconds=900)  # 15 minutes
            forget_user = ForgotPassword.objects.create(id=uuid.uuid4(), user=user, expiry=expiry,
                                                        created_at=created_at)
            email_host_user = decouple.config("EMAIL_HOST_USER")
            subject = "Password Reset Requested"
            to = [user.email]
            domain = decouple.config("FR_DOMAIN_NAME")
            message = f"Reset your password with this link {domain}/reset-password?token={forget_user.id}"
            send_mail(subject, message, email_host_user,
                      to, fail_silently=False)
            return CustomResponse(general_message="Forgot Password Email Send Successfully").get_success_response()
        else:
            return CustomResponse(general_message="User not exist").get_failure_response()


class ResetPasswordVerifyTokenAPI(APIView):
    def post(self, request, token):
        forget_user = ForgotPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = DateTimeUtils.get_current_utc_time()

            if forget_user.expiry > current_time:
                muid = forget_user.user.mu_id
                return CustomResponse(response={"muid": muid}).get_success_response()
            else:
                forget_user.delete()
                return CustomResponse(general_message="Link is expired").get_failure_response()
        else:
            return CustomResponse(general_message="Invalid Token").get_failure_response()


class ResetPasswordConfirmAPI(APIView):
    def post(self, request, token):
        forget_user = ForgotPassword.objects.filter(id=token).first()

        if forget_user:
            current_time = DateTimeUtils.get_current_utc_time()
            if forget_user.expiry > current_time:
                new_password = request.data.get("password")
                hashed_pwd = make_password(new_password)
                forget_user.user.password = hashed_pwd
                forget_user.user.save()
                forget_user.delete()
                return CustomResponse(general_message="New Password Saved Successfully").get_success_response()
            else:
                forget_user.delete()
                return CustomResponse(general_message="Link is expired").get_failure_response()
        else:
            return CustomResponse(general_message="Invalid Token").get_failure_response()

