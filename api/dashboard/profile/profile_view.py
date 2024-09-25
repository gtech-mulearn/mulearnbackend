from io import BytesIO

import qrcode
import requests
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db.models import Prefetch
from PIL import Image
from rest_framework.views import APIView

from db.organization import UserOrganizationLink
from db.task import InterestGroup, KarmaActivityLog, Level, UserIgLink
from db.user import Role, Socials, User, UserRoleLink, UserSettings
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import WebHookActions, WebHookCategory, TFPTasksHashtags
from utils.utils import DiscordWebhooks

from . import profile_serializer
from .profile_serializer import LinkSocials
from .profile_serializer import UserTermSerializer


class UserProfileEditView(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()

        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        serializer = profile_serializer.UserProfileEditSerializer(user, many=False)

        return CustomResponse(response=serializer.data).get_success_response()

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)

        serializer = profile_serializer.UserProfileEditSerializer(
            user, data=request.data, partial=True
        )

        if serializer.is_valid():
            serializer.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.USER_NAME.value,
                WebHookActions.UPDATE.value,
                user_id,
            )

            return CustomResponse(response=serializer.data).get_success_response()

        return CustomResponse(response=serializer.errors).get_failure_response()

    def delete(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id).delete()

        return CustomResponse(
            general_message="User deleted successfully"
        ).get_success_response()


class UserIgEditView(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_ig = InterestGroup.objects.filter(user_ig_link_ig__user_id=user_id).all()

        serializer = profile_serializer.UserIgListSerializer(user_ig, many=True)

        return CustomResponse(response=serializer.data).get_success_response()

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)

        serializer = profile_serializer.UserIgEditSerializer(
            user, data=request.data, partial=True
        )

        if not serializer.is_valid():
            return CustomResponse(response=serializer.errors).get_failure_response()

        serializer.save()
        DiscordWebhooks.general_updates(
            WebHookCategory.USER.value,
            WebHookActions.UPDATE.value,
            user_id,
        )
        return CustomResponse(
            general_message="Interest Group edited successfully"
        ).get_success_response()


class UserProfileAPI(APIView):
    def get(self, request, muid=None):
        user = (
            User.objects.prefetch_related(
                Prefetch(
                    "user_organization_link_user",
                    queryset=UserOrganizationLink.objects.select_related(
                        "org", "department"
                    ),
                ),
                Prefetch(
                    "user_role_link_user",
                    queryset=UserRoleLink.objects.select_related("role").filter(
                        verified=True
                    ),
                    to_attr="verified_roles",
                ),
                Prefetch(
                    "user_ig_link_user",
                    queryset=UserIgLink.objects.select_related("ig"),
                ),
            )
            .select_related("wallet_user")
            .get(muid=muid or JWTUtils.fetch_muid(request))
        )

        if muid:
            user_settings = UserSettings.objects.filter(user_id=user).first()

            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()

        else:
            JWTUtils.is_jwt_authenticated(request)

        serializer = profile_serializer.UserProfileSerializer(user, many=False)

        return CustomResponse(response=serializer.data).get_success_response()


class UserLogAPI(APIView):
    def get(self, request, muid=None):
        if muid is not None:
            user = User.objects.filter(muid=muid).first()

            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(user_id=user).first()

            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()
            user_id = user.id

        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)

        karma_activity_log = KarmaActivityLog.objects.filter(
            user=user_id, appraiser_approved=True
        ).order_by("-created_at")

        if karma_activity_log is None:
            return CustomResponse(
                general_message="No karma details available for user"
            ).get_success_response()

        serializer = profile_serializer.UserLogSerializer(karma_activity_log, many=True)

        return CustomResponse(response=serializer.data).get_success_response()


class ShareUserProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_settings = UserSettings.objects.filter(user_id=user_id).first()

        if user_settings is None:
            return CustomResponse(
                general_message="No data available"
            ).get_failure_response()

        serializer = profile_serializer.ShareUserProfileUpdateSerializer(
            user_settings, data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            general_message = (
                "Unleash your vibe, share your profile!"
                if user_settings.is_public
                else "Embrace privacy, safeguard your profile."
            )

            return CustomResponse(
                general_message=general_message
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()

    # function for generating profile qr code

    def get(self, request, uuid=None):
        fs = FileSystemStorage()
        if uuid is not None:
            user = User.objects.filter(id=uuid).first()

            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(user_id=user).first()

            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()
            user_uuid = JWTUtils.fetch_user_id(request)
            data = f"{settings.FR_DOMAIN_NAME}/profile/{user_uuid}"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            logo_url = (
                f"{settings.FR_DOMAIN_NAME}/favicon.ico/"  # Replace with your logo URL
            )
            logo_response = requests.get(logo_url)

            if logo_response.status_code == 200:
                logo_image = Image.open(BytesIO(logo_response.content))
            else:
                return CustomResponse(
                    general_message="Failed to download the logo from the URL"
                ).get_failure_response()

            logo_width, logo_height = logo_image.size
            basewidth = 100
            wpercent = basewidth / float(logo_width)
            hsize = int((float(logo_height) * float(wpercent)))
            resized_logo = logo_image.resize((basewidth, hsize))

            QRcode = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)

            QRcode.add_data(data)
            QRcolor = "black"
            QRimg = QRcode.make_image(fill_color=QRcolor, back_color="white").convert(
                "RGB"
            )

            pos = (
                (QRimg.size[0] - resized_logo.size[0]) // 2,
                (QRimg.size[1] - resized_logo.size[1]) // 2,
            )
            # image = Image.open(BytesIO("image_response.content"))
            QRimg.paste(resized_logo, pos)
            image_io = BytesIO()
            QRimg.save(image_io, format="PNG")
            image_io.seek(0)
            image_data: bytes = image_io.getvalue()
            file_path = f"user/qr/{user_uuid}.png"
            fs.exists(file_path) and fs.delete(file_path)
            file = fs.save(file_path, ContentFile(image_io.read()))

            return CustomResponse(
                general_message="QR code image with logo saved locally"
            ).get_success_response()


class UserLevelsAPI(APIView):
    def get(self, request, muid=None):
        if muid is not None:
            user = User.objects.filter(muid=muid).first()

            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(user_id=user).first()

            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()

            user_id = user.id
        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)

        user_levels_link_query = Level.objects.all().order_by("level_order")
        serializer = profile_serializer.UserLevelSerializer(
            user_levels_link_query, many=True, context={"user_id": user_id}
        )

        return CustomResponse(response=serializer.data).get_success_response()


class UserRankAPI(APIView):
    def get(self, request, muid):
        user = User.objects.filter(muid=muid).first()

        if user is None:
            return CustomResponse(general_message="Invalid muid").get_failure_response()

        roles = [role.role.title for role in UserRoleLink.objects.filter(user=user)]

        serializer = profile_serializer.UserRankSerializer(
            user, many=False, context={"roles": roles}
        )
        return CustomResponse(response=serializer.data).get_success_response()


class GetSocialsAPI(APIView):
    def get(self, request, muid=None):
        if muid is not None:
            user = User.objects.filter(muid=muid).first()
            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(user_id=user).first()

            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()

            user_id = user.id
        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)

        social_instance = Socials.objects.filter(user_id=user_id).first()

        serializer = LinkSocials(instance=social_instance)

        return CustomResponse(response=serializer.data).get_success_response()


class SocialsAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        social_instance = Socials.objects.filter(user_id=user_id).first()

        serializer = LinkSocials(
            instance=social_instance, data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="Socials Updated"
            ).get_success_response()

        return CustomResponse(response=serializer.errors).get_failure_response()


class ResetPasswordAPI(APIView):
    authentication_classes = [CustomizePermission]

    def post(self, request):
        user_muid = JWTUtils.fetch_muid(request)
        user = User.objects.filter(muid=user_muid).first()

        if user is None:
            return CustomResponse(
                general_message="No user data available"
            ).get_failure_response()

        return self.save_password(request, user)

    def save_password(self, request, user_obj):
        new_password = request.data.get("password")
        hashed_pwd = make_password(new_password)

        user_obj.password = hashed_pwd
        user_obj.save()
        return CustomResponse(
            general_message="New Password Saved Successfully"
        ).get_success_response()


class QrcodeRetrieveAPI(APIView):
    def get(self, request, uuid):
        try:
            user = User.objects.prefetch_related().get(
                id=uuid or JWTUtils.fetch_user_id(request)
            )

            user_settings = UserSettings.objects.filter(user_id=user).first()

            if not user_settings.is_public:
                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()

            serializer = profile_serializer.UserShareQrcode(
                user, many=False, context={"request": request}
            )

            return CustomResponse(response=serializer.data).get_success_response()

        except User.DoesNotExist:
            return CustomResponse(
                response="The given UUID seems to be invalid"
            ).get_failure_response()


class BadgesAPI(APIView):
    def get(self, request, muid):
        try:
            user = User.objects.get(muid=muid)
            hastags = TFPTasksHashtags.get_all_values()
            response_data = {"full_name": user.full_name, "completed_tasks": []}
            for tag in hastags:
                if log := KarmaActivityLog.objects.filter(
                    user=user, task__hashtag=tag
                ).first():
                    response_data["completed_tasks"].append(log.task.title)
            return CustomResponse(response=response_data).get_success_response()
        except User.DoesNotExist:
            return CustomResponse(
                response="The given muid seems to be invalid"
            ).get_failure_response()


class UsertermAPI(APIView):
    def post(self, request, muid):
        try:
            user = User.objects.get(muid=muid)
        except User.DoesNotExist:
            return CustomResponse(
                response="The user does not exist"
            ).get_failure_response()

        try:
            settings = UserSettings.objects.get(user=user)
        except UserSettings.DoesNotExist:
            return CustomResponse(
                response="The user settings don't exist"
            ).get_failure_response()

        serializer = UserTermSerializer(
            settings, data={"is_userterms_approved": True}, partial=True
        )
        if serializer.is_valid():
            settings = serializer.save()
            if settings.is_userterms_approved:
                response_data = {
                    "message": "User terms have been successfully approved."
                }
                return CustomResponse(response=response_data).get_success_response()
            else:
                response_data = {
                    "message": "The user terms have not been successfully approved."
                }
                return CustomResponse(response=response_data).get_failure_response()
        return CustomResponse(response="Invalid data provided").get_failure_response()

    def get(self, request, muid):
        try:
            user = User.objects.get(muid=muid)
        except User.DoesNotExist:
            return CustomResponse(
                response="The user does not exist"
            ).get_failure_response()

        try:
            settings = UserSettings.objects.get(user=user)
        except UserSettings.DoesNotExist:
            return CustomResponse(
                response="The user settings don't exist"
            ).get_failure_response()

        if settings.is_userterms_approved:
            response_data = {"message": "User terms are approved."}
            return CustomResponse(response=response_data).get_success_response()
        else:
            response_data = {"message": "User terms are not approved."}
            return CustomResponse(response=response_data).get_failure_response()
