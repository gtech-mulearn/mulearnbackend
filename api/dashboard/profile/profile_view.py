from django.db.models import Prefetch
from rest_framework.views import APIView
import qrcode
import requests
import decouple
from PIL import Image
from io import BytesIO
from db.organization import UserOrganizationLink
from db.task import InterestGroup, KarmaActivityLog, Level
from db.user import Role
from db.user import User, UserSettings, UserRoleLink, Socials
from utils.exception import CustomException
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import WebHookActions, WebHookCategory
from utils.utils import DiscordWebhooks
from . import profile_serializer
from .profile_serializer import LinkSocials


class UserProfileEditView(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()

        if not user:
            return CustomResponse(
                general_message="User Not Exists"
            ).get_failure_response()

        serializer = profile_serializer.UserProfileEditSerializer(
            user,
            many=False
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)

        serializer = profile_serializer.UserProfileEditSerializer(
            user,
            data=request.data,
            partial=True
        )

        if serializer.is_valid():
            serializer.save()

            DiscordWebhooks.general_updates(
                WebHookCategory.USER_NAME.value,
                WebHookActions.UPDATE.value,
                user_id,
            )

            return CustomResponse(
                response=serializer.data
            ).get_success_response()

        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()


class UserIgEditView(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_ig = InterestGroup.objects.filter(
            user_ig_link_ig__user_id=user_id
        ).all()

        serializer = profile_serializer.UserIgListSerializer(
            user_ig,
            many=True
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()

    def patch(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.get(id=user_id)

        serializer = profile_serializer.UserIgEditSerializer(
            user, data=request.data, partial=True
        )

        if not serializer.is_valid():

            return CustomResponse(
                response=serializer.errors
            ).get_failure_response()

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
        try:
            user = User.objects.prefetch_related(
                Prefetch(
                    "user_organization_link_user",
                    queryset=UserOrganizationLink.objects.all().select_related(
                        "org",
                        "department"
                    ),
                ),
                Prefetch(
                    "user_role_link_user__role",
                    queryset=Role.objects.all(),
                ),
            ).get(muid=muid or JWTUtils.fetch_muid(request))

            if muid:
                user_settings = UserSettings.objects.filter(
                    user_id=user
                ).first()

                if not user_settings.is_public:
                    return CustomResponse(
                        general_message="Private Profile"
                    ).get_failure_response()

            else:
                JWTUtils.is_jwt_authenticated(request)

            serializer = profile_serializer.UserProfileSerializer(
                user,
                many=False
            )

            return CustomResponse(
                response=serializer.data
            ).get_success_response()

        except User.DoesNotExist:
            return CustomResponse(
                response="The given μID seems to be invalid"
            ).get_failure_response()


class UserLogAPI(APIView):
    def get(self, request, muid=None):

        if muid is not None:
            user = User.objects.filter(
                muid=muid
            ).first()

            if user is None:

                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(
                user_id=user
            ).first()

            if not user_settings.is_public:

                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()
            user_id = user.id

        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)

        karma_activity_log = KarmaActivityLog.objects.filter(
            user=user_id,
            appraiser_approved=True
        ).order_by(
            "-created_at"
        )

        if karma_activity_log is None:
            return CustomResponse(
                general_message="No karma details available for user"
            ).get_success_response()

        serializer = profile_serializer.UserLogSerializer(
            karma_activity_log,
            many=True
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()
class ShareUserProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user_settings = UserSettings.objects.filter(
            user_id=user_id
        ).first()

        if user_settings is None:

            return CustomResponse(
                general_message="No data available "
            ).get_failure_response()

        serializer = profile_serializer.ShareUserProfileUpdateSerializer(
            user_settings,
            data=request.data,
            context={
                "request": request
            }
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

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()


class UserLevelsAPI(APIView):
    def get(self, request, muid=None):

        if muid is not None:
            user = User.objects.filter(muid=muid).first()

            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(
                user_id=user
            ).first()

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
            user_levels_link_query,
            many=True,
            context={
                "user_id": user_id
            }
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()


class UserRankAPI(APIView):
    def get(self, request, muid):
        user = User.objects.filter(
            muid=muid
        ).first()

        if user is None:
            return CustomResponse(
                general_message="Invalid muid"
            ).get_failure_response()

        roles = [role.role.title for role in UserRoleLink.objects.filter(user=user)]

        serializer = profile_serializer.UserRankSerializer(
            user,
            many=False,
            context={
                "roles": roles
            }
        )
        return CustomResponse(
            response=serializer.data
        ).get_success_response()


class GetSocialsAPI(APIView):
    def get(self, request, muid=None):

        if muid is not None:
            user = User.objects.filter(
                muid=muid
            ).first()
            if user is None:

                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(
                user_id=user
            ).first()

            if not user_settings.is_public:

                return CustomResponse(
                    general_message="Private Profile"
                ).get_failure_response()

            user_id = user.id
        else:
            JWTUtils.is_jwt_authenticated(request)
            user_id = JWTUtils.fetch_user_id(request)

        social_instance = Socials.objects.filter(
            user_id=user_id
        ).first()

        serializer = LinkSocials(
            instance=social_instance
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()


class SocialsAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        social_instance = Socials.objects.filter(
            user_id=user_id
        ).first()

        serializer = LinkSocials(
            instance=social_instance,
            data=request.data,
            context={
                "request": request
            }
        )

        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message="Socials Updated"
            ).get_success_response()

        return CustomResponse(
            response=serializer.errors
        ).get_failure_response()


# Qrcode Logic API for getting the qrcode if the user is account public 
class QrcodeCreateAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request,muid=None):
        base_url = decouple.config("FR_DOMAIN_NAME")
        print(muid,"before")
        if muid is not None:
            user = User.objects.filter(muid=muid).first() 
            print(muid,"after")
            if user is None:
                return CustomResponse(
                    general_message="Invalid muid"
                ).get_failure_response()

            user_settings = UserSettings.objects.filter(
                user_id=user
            ).first()

            if not user_settings.is_public:
                    return CustomResponse(
                        general_message="Private Profile"
                    ).get_failure_response()
            else:
                user_muid = JWTUtils.fetch_muid(request)
                data = f"{base_url}/profile/{user_muid}"

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            logo_url = "https://mulearn.org/assets/navbar/%C2%B5Learn.webp"  # Replace with your logo URL
            logo_response = requests.get(logo_url)

            if logo_response.status_code == 200:
                logo_image = Image.open(BytesIO(logo_response.content))
            else:
                return HttpResponse("Failed to download the logo from the URL", status=500)

            logo_width, logo_height = logo_image.size
            basewidth = 200
            wpercent = (basewidth / float(logo_width))
            hsize = int((float(logo_height) * float(wpercent)))
            resized_logo = logo_image.resize((basewidth, hsize), Image.ANTIALIAS)

            QRcode = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_H
            )
            QRcode.add_data(data)
            QRcolor = 'black'

            QRimg = QRcode.make_image(fill_color=QRcolor, back_color="white").convert('RGB')

            pos = ((QRimg.size[0] - resized_logo.size[0]) // 2, (QRimg.size[1] - resized_logo.size[1]) // 2)
            QRimg.paste(resized_logo, pos)

            file_path = '/home/mishal/Downloads/'+user_muid+'.png'  # Replace with your desired directory
            QRimg.save(file_path)
            return CustomResponse(
                    general_message="QR code image with logo saved locally"
                ).get_success_response()
        

        
class QrcodeRetrieveAPI(APIView):
    def get(self,request,muid):
        qrcode = requests.get(f"http://0.0.0.0:8500/{muid}.png")
        return CustomResponse(
            general_message="QR code image with logo reterived",
        ).get_success_response()
        