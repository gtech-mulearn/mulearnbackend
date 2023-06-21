from rest_framework.views import APIView

from api.dashboard.profile.serializers import UserLogSerializer, UserProfileSerializer
from db.task import KarmaActivityLog
from db.user import User, UserSettings
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import DateTimeUtils


class UserProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user = User.objects.select_related('total_karma_user').prefetch_related(
            'user_organization_link_user_id__org',
            'user_organization_link_user_id__department',
            'user_role_link_user__role',
            'userlvllink_set__level',
        ).filter(id=user_id).first()

        serializer = UserProfileSerializer(user, many=False, context={'roles': JWTUtils.fetch_role(request)})
        return CustomResponse(response=serializer.data).get_success_response()

    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        first_name = request.data.get('firstName')
        last_name = request.data.get('lastName')
        email = request.data.get('email')
        mobile = request.data.get('mobile')
        dob = request.data.get('dob')

        user_object = User.objects.filter(id=user_id).first()

        user_object.first_name = first_name
        user_object.last_name = last_name
        user_object.email = email
        user_object.mobile = mobile
        user_object.dob = dob
        user_object.save()

        return CustomResponse(general_message='profile edited successfully').get_success_response()


class UserLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        karma_activity_log = KarmaActivityLog.objects.filter(created_by=user_id, appraiser_approved=True).order_by(
            '-created_at')

        if karma_activity_log is None:
            return CustomResponse(general_message="No karma details available for user").get_success_response()

        serializer = UserLogSerializer(karma_activity_log, many=True).data
        return CustomResponse(response=serializer).get_success_response()


class ShareUserProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    def put(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        is_public = request.data.get('isPublic')

        user_settings = UserSettings.objects.filter(user=user_id).first()

        user_settings.is_public = is_public
        user_settings.updated_by = user_id
        user_settings.updated_at = DateTimeUtils.get_current_utc_time()

        user_settings.save()

        return CustomResponse(general_message='Now your profile is shareable').get_success_response()


class AccessUserProfileAPI(APIView):

    def get(self, request, muid):

        user = User.objects.filter(mu_id=muid).first()
        if user is None:
            return CustomResponse(general_message='invalid muid').get_success_response()

        user_settings = UserSettings.objects.filter(user_id=user).first()

        if user_settings.is_public == 1:
            serializer = UserProfileSerializer(user, many=False)
            return CustomResponse(response=serializer.data).get_success_response()

        else:
            return CustomResponse(general_message='User profile is privet').get_success_response()
