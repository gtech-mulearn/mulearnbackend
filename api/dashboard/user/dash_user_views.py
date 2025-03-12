import uuid
from datetime import timedelta

from decouple import config as decouple_config
from django.contrib.auth.hashers import make_password
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from rest_framework.views import APIView

from db.user import ForgotPassword, User, UserRoleLink
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, WebHookActions, WebHookCategory
from utils.utils import CommonUtils, DateTimeUtils, DiscordWebhooks, send_template_mail
from . import dash_user_serializer
from django.core.cache import cache

BE_DOMAIN_NAME = decouple_config("BE_DOMAIN_NAME")


class UserInfoAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_muid = JWTUtils.fetch_muid(request)
        user = cache.get(f"db_user_{user_muid}")
        if not user:
            user = User.objects.filter(muid=user_muid).first()
            cache.set(f"db_user_{user_muid}", user, timeout=10)
        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        response = dash_user_serializer.UserSerializer(user, many=False).data

        return CustomResponse(response=response).get_success_response()


class UserGetPatchDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request, user_id):
        user = User.objects.filter(id=user_id).first()

        if user is None:
            return CustomResponse(
                general_message="User Not Available"
            ).get_failure_response()

        serializer = dash_user_serializer.UserDetailsSerializer(user)

        return CustomResponse(response=serializer.data).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id).delete()
            return CustomResponse(
                general_message="User deleted successfully"
            ).get_success_response()
        except User.DoesNotExist as e:
            return CustomResponse(general_message=str(e)).get_failure_response()

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, user_id):
        user = User.objects.get(id=user_id)

        request.data["admin"] = JWTUtils.fetch_user_id(request)

        serializer = dash_user_serializer.UserDetailsEditSerializer(
            user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.USER.value, WebHookActions.UPDATE.value, user_id
            )
            return CustomResponse(
                general_message="User Edited Successfully"
            ).get_success_response()

        return CustomResponse(general_message=serializer.errors).get_failure_response()


class UserAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        user_queryset = User.objects.select_related(
            "wallet_user", "user_lvl_link_user", "user_lvl_link_user__level"
        ).all()

        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            [
                "muid",
                "full_name",
                "email",
                "mobile",
                "user_lvl_link_user__level__name",
            ],
            {
                "full_name": "full_name",
                "karma": "wallet_user__karma",
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
        user_queryset = User.objects.select_related(
            "wallet_user", "user_lvl_link_user", "user_lvl_link_user__level"
        ).all()

        serializer = dash_user_serializer.UserDashboardSerializer(
            user_queryset, many=True
        )

        return CommonUtils.generate_csv(serializer.data, "User")


class UserVerificationAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        user_queryset = UserRoleLink.objects.select_related("user", "role").filter(
            verified=False
        )

        queryset = CommonUtils.get_paginated_queryset(
            user_queryset,
            request,
            search_fields=[
                "user__full_name",
                "user__mobile",
                "user__email",
                "user__muid",
                "role__title",
            ],
            sort_fields={
                "full_name": "user__full_name",
                "role_title": "role__title",
                "muid": "user__muid",
                "email": "user__email",
                "mobile": "user__mobile",
            },
        )
        serializer = dash_user_serializer.UserVerificationSerializer(
            queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=queryset.get("pagination")
        )

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, link_id):
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
            context=user_data,
            subject="Role request at μLearn!",
            address=["mentor_verification.html"],
        )

        return CustomResponse(
            response={"user_role_link": user_data}
        ).get_success_response()

    @role_required([RoleType.ADMIN.value])
    def delete(self, request, link_id):
        link = UserRoleLink.objects.get(id=link_id)
        link.delete()

        return CustomResponse(
            general_message="Link deleted successfully"
        ).get_success_response()


class UserVerificationCSV(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        user_queryset = UserRoleLink.objects.select_related("user", "role").filter(
            verified=False
        )

        serializer = dash_user_serializer.UserVerificationSerializer(
            user_queryset, many=True
        )
        return CommonUtils.generate_csv(serializer.data, "User")


class ForgotPasswordAPI(APIView):
    def post(self, request):
        email_muid = request.data.get("emailOrMuid")

        if not (
            user := User.objects.filter(
                Q(muid=email_muid) | Q(email=email_muid)
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
            muid = forget_user.user.muid
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


class UserProfilePictureView(APIView):
    # def get(self, request, user_id):
    #     user = User.objects.filter(id=user_id).first()

    #     if user is None:
    #         return CustomResponse(
    #             general_message="No user data available"
    #         ).get_failure_response()
    #     image_path = f'user/profile/{user_id}.png'
    #     response = ImageResponse(path=image_path)
    #     if response.exists():
    #         return response.get_success_response()
    #     else:
    #         return CustomResponse(
    #             general_message="No Profile picture available"
    #         ).get_failure_response()

    def patch(self, request):
        DiscordWebhooks.general_updates(
            WebHookCategory.USER_PROFILE.value,
            WebHookActions.UPDATE.value,
            JWTUtils.fetch_user_id(request),
        )
        return CustomResponse(
            general_message="Successfully updated"
        ).get_success_response()

    def post(self, request):
        user_id = request.data.get("user_id")
        user = User.objects.filter(id=user_id).first()

        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        pic = request.FILES.get("profile")

        if pic is None:
            return CustomResponse(
                general_message="No profile picture"
            ).get_failure_response()

        if not pic.content_type.startswith("image/"):
            return CustomResponse(
                general_message="Expected an image"
            ).get_failure_response()

        extention = ".png"  # os.path.splitext(pic.name)[1]
        fs = FileSystemStorage()
        filename = f"user/profile/{user_id}{extention}"
        if fs.exists(filename):
            fs.delete(filename)
        filename = fs.save(filename, pic)
        file_url = fs.url(filename)
        uploaded_file_url = f"{BE_DOMAIN_NAME}{file_url}"

        return CustomResponse(
            response={"user_id": user.id, "profile_pic": uploaded_file_url}
        ).get_success_response()
