from api.dashboard.profile.serializers import UserLogSerializer, UserInterestGroupSerializer
from db.task import KarmaActivityLog, TotalKarma, UserIgLink
from db.user import User
from db.organization import UserOrganizationLink
from rest_framework.views import APIView
from utils.response import CustomResponse
from utils.permission import CustomizePermission, JWTUtils


class UserProfileAPI(APIView):
    authentication_classes = [CustomizePermission]

    def get(self, request):

        user_id = JWTUtils.fetch_user_id(request)

        user = User.objects.filter(id=user_id).first()
        return CustomResponse(response={
            'name': user.first_name + user.last_name,
            'email': user.email,
            'mobile': user.mobile,
            'dob': user.dob,
            'gender': user.gender,
        }).get_success_response()


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
        return CustomResponse(response=serializer).get_failure_response()
