import uuid
from datetime import timedelta

import decouple
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.db.models import Case, CharField, F, Q, Value, When
from rest_framework.views import APIView

from db.user import ForgotPassword, User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import OrganizationType, RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DateTimeUtils, DiscordWebhooks, send_template_mail
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
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            serializer = dash_user_serializer.UserDetailsEditSerializer(user).data
            return CustomResponse(response=serializer).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            user.active = False
            user.save()
            return CustomResponse(
                general_message="User deleted successfully"
            ).get_success_response()

        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            admin_id = JWTUtils.fetch_user_id(request)
            admin = User.objects.get(id=admin_id)
            serializer = dash_user_serializer.UserDetailsEditSerializer(
                user, data=request.data, partial=True, context={"admin": admin}
            )
            if serializer.is_valid():
                serializer.save()
                DiscordWebhooks.general_updates(
                    WebHookCategory.USER.value,
                    WebHookActions.UPDATE.value,
                    user_id,
                )

                return CustomResponse(
                    general_message=serializer.data
                ).get_success_response()
            return CustomResponse(
                general_message=serializer.errors
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        user_queryset = User.objects.filter(active=True).annotate(
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

        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["mu_id", "first_name", "last_name", "email", "mobile", "discord_id"],
            {
                "first_name": "first_name",
                "total_karma": "total_karma",
                "email": "email",
                "created_at": "created_at",
            },
        )
        serializer = dash_user_serializer.UserDashboardSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )


class UserManagementCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
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

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        user_queryset = UserRoleLink.objects.filter(verified=False)
        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            ["user__first_name", "user__last_name", "role__title"],
            {"fullname": "fullname"},
        )
        serializer = dash_user_serializer.UserVerificationSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, link_id):
        try:
            user = UserRoleLink.objects.get(id=link_id)

            user_serializer = dash_user_serializer.UserVerificationSerializer(
                user, data=request.data, partial=True
            )

            if not user_serializer.is_valid():
                return CustomResponse(
                    general_message=user_serializer.errors
                ).get_failure_response()

            user_serializer.save()
            user_data = user_serializer.data

            DiscordWebhooks.general_updates(
                WebHookCategory.USER_ROLE.value,
                WebHookActions.UPDATE.value,
                user_data["user_id"],
            )

            send_template_mail(
                user_data=user_data,
                subject="Role request at μLearn!",
                address=("mentor_verification.html"),
            )

            return CustomResponse(
                response={"user_role_link": user_data}
            ).get_success_response()
        except Exception as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
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
        forget_user = ForgotPassword.objects.create(
            id=uuid.uuid4(), user=user, expiry=expiry, created_at=created_at
        )

        receiver_mail = user.email
        html_address = ["forgot_password.html"]
        context = {
            "email": receiver_mail,
            "token": forget_user.id,
        }

        send_template_mail(
            context=context,
            subject="Password Reset Requested",
            address=html_address,
        )

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
        if User.objects.filter(email=email).exists():
            return CustomResponse(
                general_message="User already exist"
            ).get_failure_response()

        domain = decouple.config('FR_DOMAIN_NAME')
        from_mail = decouple.config('FROM_MAIL')
        to = [email]
        message = f"Hi, \n\nYou have been invited to join the MuLearn community. Please click on the link below to join.\n\n{domain}\n\nThanks,\nMuLearn Team"
        send_mail(
            "Invitation to join MuLearn",
            message,
            from_mail,
            to,
            fail_silently=False,
        )
        return CustomResponse(
            general_message="Invitation sent successfully"
        ).get_success_response()
