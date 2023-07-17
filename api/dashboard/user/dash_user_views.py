import uuid
from datetime import timedelta

import decouple
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Case, CharField, F, Q, Value, When
from rest_framework.views import APIView

from db.user import ForgotPassword, User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType
from utils.utils import CommonUtils, DateTimeUtils

from . import dash_user_serializer


class UserInfoAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_muid = JWTUtils.fetch_muid(request)
        user = User.objects.filter(mu_id=user_muid).first()

        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        response = dash_user_serializer.UserSerializer(user, many=False).data
        return CustomResponse(response=response).get_success_response()


class UserEditAPI(APIView):
    # authentication_classes = [CustomizePermission]

    # @role_required([RoleType.ADMIN.value, ])
    def get(self, request, user_id):
        user = (
            User.objects.filter(id=user_id)
            .prefetch_related("user_organization_link_user_id")
            .first()
        )
        serializer = dash_user_serializer.UserDetailsSerializer(user)
        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value, ])
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return CustomResponse(
                general_message="User deleted successfully"
            ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value, ])
    def put(self, request, user_id):
        user = User.objects.get(id=user_id)
        serializer = dash_user_serializer.UserEditSerializer(
            user, data=request.data, partial=True
        )

        if not serializer.is_valid():
            return CustomResponse(response=serializer.errors).get_failure_response()

        try:
            serializer.save()
            return CustomResponse(response=serializer.data).get_success_response()

        except IntegrityError as e:
            return CustomResponse(response=str(e)).get_failure_response()


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request, user_id=None):
        user_queryset = User.objects.annotate(
            total_karma=Case(
                When(total_karma_user__isnull=False, then=F("total_karma_user__karma")),
                default=Value(0),
            ),
            company=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COMPANY.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
            department=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__department__title"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            graduation_year=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__graduation_year"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            college=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COLLEGE.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
        )

        if user_id:
            user_data = user_queryset.filter(id=user_id)
            if not user_data:
                return CustomResponse(general_message="User not found").get_failure_response()
            serializer = dash_user_serializer.UserDashboardSerializer(user_data, many=True)
            return CustomResponse(response=serializer.data).get_success_response()
        else:
            queryset = CommonUtils.get_paginated_queryset(
                user_queryset,
                request,
                ["mu_id", "first_name", "last_name", "email", "mobile"],
            )
            serializer = dash_user_serializer.UserDashboardSerializer(
                queryset.get("queryset"), many=True
            )

            return CustomResponse().paginated_response(
                data=serializer.data, pagination=queryset.get("pagination")
            )


class UserManagementCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        user_queryset = User.objects.annotate(
            total_karma=Case(
                When(total_karma_user__isnull=False, then=F("total_karma_user__karma")),
                default=Value(0),
            ),
            company=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COMPANY.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
            department=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__department__title"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            graduation_year=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    then=F("user_organization_link_user_id__graduation_year"),
                ),
                default=Value(""),
                output_field=CharField(),
            ),
            college=Case(
                When(
                    user_organization_link_user_id__verified=True,
                    user_organization_link_user_id__org__org_type=OrganizationType.COLLEGE.value,
                    then=F("user_organization_link_user_id__org__title"),
                ),
                default=Value(None),
                output_field=CharField(),
            ),
        )
        user_serializer_data = dash_user_serializer.UserDashboardSerializer(
            user_queryset, many=True
        ).data
        return CommonUtils.generate_csv(user_serializer_data, "User")


class UserVerificationAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value, ])
    def get(self, request):
        user_queryset = UserRoleLink.objects.filter(verified=False)
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["first_name", "last_name", "role_title"],
        )
        serializer = dash_user_serializer.UserVerificationSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value, ])
    def patch(self, request, link_id):
        try:
            user = UserRoleLink.objects.get(id=link_id)
        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

        serializer = dash_user_serializer.UserVerificationSerializer(
            user, data=request.data, partial=True
        )

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

    @role_required([RoleType.ADMIN.value, ])
    def delete(self, request, link_id):
        try:
            link = UserRoleLink.objects.get(id=link_id)
            link.delete()
            return CustomResponse(
                general_message=["Link deleted successfully"]
            ).get_success_response()

        except ObjectDoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class ForgotPasswordAPI(APIView):
    def post(self, request):
        email_muid = request.data.get("emailOrMuid")

        if not (
            user := User.objects.filter(
                Q(mu_id=email_muid) | Q(email=email_muid)
            ).first()
        ):
            return CustomResponse(
                general_message="User not exist"
            ).get_failure_response()
        created_at = DateTimeUtils.get_current_utc_time()
        expiry = created_at + timedelta(seconds=900)  # 15 minutes
        forget_user = ForgotPassword.objects.create(  #
            id=uuid.uuid4(), user=user, expiry=expiry, created_at=created_at
        )
        email_host_user = decouple.config("EMAIL_HOST_USER")
        to = [user.email]

        domain = decouple.config("FR_DOMAIN_NAME")
        message = f"Reset your password with this link {domain}/reset-password?token={forget_user.id}"
        subject = "Password Reset Requested"
        send_mail(subject, message, email_host_user, to, fail_silently=False)
        return CustomResponse(
            general_message="Forgot Password Email Send Successfully"
        ).get_success_response()


class ResetPasswordVerifyTokenAPI(APIView):
    def post(self, request, token):
        if not (forget_user := ForgotPassword.objects.filter(id=token).first()):
            return CustomResponse(
                general_message="Invalid Token"
            ).get_failure_response()
        current_time = DateTimeUtils.get_current_utc_time()

        if forget_user.expiry > current_time:
            muid = forget_user.user.mu_id
            return CustomResponse(response={"muid": muid}).get_success_response()
        else:
            forget_user.delete()
            return CustomResponse(
                general_message="Link is expired"
            ).get_failure_response()


class ResetPasswordConfirmAPI(APIView):
    def post(self, request, token):
        if not (forget_user := ForgotPassword.objects.filter(id=token).first()):
            return CustomResponse(
                general_message="Invalid Token"
            ).get_failure_response()
        current_time = DateTimeUtils.get_current_utc_time()
        if forget_user.expiry > current_time:
            return self.save_password(request, forget_user)
        forget_user.delete()
        return CustomResponse(general_message="Link is expired").get_failure_response()

    def save_password(self, request, forget_user):
        new_password = request.data.get("password")
        hashed_pwd = make_password(new_password)
        forget_user.user.password = hashed_pwd
        forget_user.user.save()
        forget_user.delete()
        return CustomResponse(
            general_message="New Password Saved Successfully"
        ).get_success_response()


class UserInviteAPI(APIView):
    def post(self, request):
        email = request.data.get("email")
        if User.objects.filter(email=email).exists() :
            return CustomResponse(
                general_message="User already exist"
            ).get_failure_response()
        
        email_host_user = decouple.config("EMAIL_HOST_USER")
        to = [email]
        domain = decouple.config("FR_DOMAIN_NAME")
        message = f"Hi, \n\nYou have been invited to join the MuLearn community. Please click on the link below to join.\n\n{domain}\n\nThanks,\nMuLearn Team"
        send_mail(
            "Invitation to join MuLearn",
            message,
            email_host_user,
            to,
            fail_silently=False,
        )
        return CustomResponse(
            general_message="Invitation sent successfully"
        ).get_success_response()