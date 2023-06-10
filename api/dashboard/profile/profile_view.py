from rest_framework.views import APIView

from api.dashboard.profile.serializers import UserLogSerializer, UserInterestGroupSerializer, UserSuggestionSerializer, \
    UserProfileSerializer
from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog, TotalKarma, UserIgLink
from db.user import User
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse


class UserProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        user = User.objects.filter(id=user_id).first()
        serializer = UserProfileSerializer(user, many=False)
        return CustomResponse(response=serializer.data).get_success_response()


class EditUserDetailsAPI(APIView):
    authentication_classes = [CustomizePermission]

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
        karma_activity_log = KarmaActivityLog.objects.filter(created_by=user_id).all()

        if karma_activity_log is None:
            return CustomResponse(general_message="No karma details available for user").get_success_response()

        serializer = UserLogSerializer(karma_activity_log, many=True).data
        return CustomResponse(response=serializer).get_success_response()


class UserTaskLogAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        karma = TotalKarma.objects.filter(user_id=user_id).first()
        if karma is None:
            return CustomResponse(general_message='Karma details note available for user').get_failure_response()

        org_link = UserOrganizationLink.objects.filter(user_id=user_id).first()
        if org_link is None:
            return CustomResponse(general_message='No organization details available for user').get_failure_response()

        total_karma = TotalKarma.objects.all().order_by('-karma')
        rank = 1
        for data in total_karma:
            if data != karma:
                rank += 1
            else:
                break
        return CustomResponse(response={
            'userKarma': karma.karma,
            'OrgCode': org_link.org.code,
            'rank': rank
        }).get_success_response()


class UserInterestGroupAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        org_link = UserIgLink.objects.filter(user_id=user_id).all()
        serializer = UserInterestGroupSerializer(org_link, many=True).data
        return CustomResponse(response=serializer).get_success_response()


class UserSuggestionAPI(APIView):

    def get(self, request):
        total_karma_object = TotalKarma.objects.all().order_by('-karma')[:5]
        if total_karma_object is None:
            return CustomResponse(general_message='No Karma Related data available').get_failure_response()

        serializer = UserSuggestionSerializer(total_karma_object, many=True).data
        return CustomResponse(response=serializer).get_success_response()
