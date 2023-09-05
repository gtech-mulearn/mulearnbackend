from decouple import config
from rest_framework.views import APIView

from api.notification.notifications_utils import NotificationUtils
from db.learning_circle import LearningCircle, UserCircleLink
from db.organization import UserOrganizationLink
from db.user import User
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.types import OrganizationType
from .dash_lc_serializer import LearningCircleSerializer, LearningCircleCreateSerializer, LearningCircleHomeSerializer, \
    LearningCircleUpdateSerializer, LearningCircleJoinSerializer, LearningCircleMeetSerializer, \
    LearningCircleMainSerializer, LearningCircleNoteSerializer , LearningCircleDataSerializer

domain = config("FR_DOMAIN_NAME")


class LearningCircleAPI(APIView):
    def get(self, request):  # lists the learning circle in the user's college
        user_id = JWTUtils.fetch_user_id(request)
        org_id = UserOrganizationLink.objects.filter(user_id=user_id,
                                                     org__org_type=OrganizationType.COLLEGE.value).values_list('org_id',
                                                                                                               flat=True).first()
        learning_queryset = LearningCircle.objects.filter(org=org_id).exclude(
            usercirclelink__accepted=1, usercirclelink__user_id=user_id
        )
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)
        return CustomResponse(response=learning_serializer.data).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = LearningCircleCreateSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            circle = serializer.save()
            return CustomResponse(general_message='LearningCircle created successfully',
                                  response={'circle_id': circle.id}).get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LearningCircleJoinApi(APIView):
    def post(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        full_name = f'{user.first_name} {user.last_name}' if user.last_name else user.first_name
        lc = UserCircleLink.objects.filter(circle_id=circle_id, lead=True).first()
        serializer = LearningCircleJoinSerializer(data=request.data,
                                                  context={'user_id': user_id, 'circle_id': circle_id})
        if serializer.is_valid():
            serializer.save()
            NotificationUtils.insert_notification(user_id=lc.user_id,
                                                  title="Member Request",
                                                  description=f"{full_name} has requested to join your learning circle",
                                                  button="LC",
                                                  url=f'{domain}/api/v1/dashboard/lc/{circle_id}/{user_id}/',
                                                  created_by=user)
            return CustomResponse(general_message='Request sent').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LearningCircleListApi(APIView):
    def get(self, request):  # Lists user's learning circle
        user_id = JWTUtils.fetch_user_id(request)
        learning_queryset = LearningCircle.objects.filter(usercirclelink__user_id=user_id, usercirclelink__accepted=1)
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)
        return CustomResponse(response=learning_serializer.data).get_success_response()


class LearningCircleMeetAPI(APIView):
    def patch(self, request, circle_id):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleMeetSerializer(learning_circle, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Meet updated successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class LearningCircleHomeApi(APIView):
    def get(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleHomeSerializer(learning_circle, many=False, context={"user_id": user_id})
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request, member_id, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle_link = UserCircleLink.objects.filter(user_id=member_id, circle_id=circle_id).first()
        serializer = LearningCircleUpdateSerializer()
        serializer.destroy(learning_circle_link)
        return CustomResponse(general_message='Removed successfully').get_success_response()

    def patch(self, request, member_id, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle_link = UserCircleLink.objects.filter(user_id=member_id, circle_id=circle_id).first()
        serializer = LearningCircleUpdateSerializer(learning_circle_link, data=request.data,
                                                    context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            is_accepted = request.data.get('is_accepted')
            if is_accepted == '1':
                NotificationUtils.insert_notification(member_id, title="Request approved",
                                                      description="You request to join the learning circle has been approved",
                                                      button="LC",
                                                      url=f'{domain}/api/v1/dashboard/lc/{circle_id}/',
                                                      created_by=User.objects.filter(id=user_id).first())
            else:
                NotificationUtils.insert_notification(member_id, title="Request rejected",
                                                      description="You request to join the learning circle has been rejected",
                                                      button="LC",
                                                      url=f'{domain}/api/v1/dashboard/lc/join',
                                                      created_by=User.objects.filter(id=user_id).first())
            return CustomResponse(general_message='Approved successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    def put(self, request, circle_id):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleNoteSerializer(learning_circle, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(general_message='Note updated successfully').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()

    def delete(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        usr_circle_link = UserCircleLink.objects.filter(
            circle__id=circle_id,
            user__id=user_id
        ).first()

        if not usr_circle_link:
            return CustomResponse(general_message='User not part of circle').get_error_response()

        if usr_circle_link.lead:
            if (
                    next_lead := UserCircleLink.objects.filter(
                        circle__id=circle_id, accepted=1
                    )
                            .exclude(user__id=user_id)
                            .order_by('accepted_at')
                            .first()
            ):
                next_lead.lead = True
                next_lead.save()
                usr_circle_link.delete()
                return CustomResponse(general_message='Leadership transferred').get_success_response()

        usr_circle_link.delete()

        if not UserCircleLink.objects.filter(circle__id=circle_id).exists():
            LearningCircle.objects.filter(id=circle_id).delete()
            return CustomResponse(general_message='Learning Circle Deleted').get_success_response()

        return CustomResponse(general_message='Left').get_success_response()


class LearningCircleMainApi(APIView):
    def post(self, request):
        all_circles = LearningCircle.objects.all()
        ig_id = request.data.get('ig_id')
        org_id = request.data.get('org_id')
        district_id = request.data.get('district_id')

        if district_id:
            all_circles = all_circles.filter(org__district_id=district_id)

        if org_id:
            all_circles = all_circles.filter(org_id=org_id)

        if ig_id:
            all_circles = all_circles.filter(ig_id=ig_id)

        if ig_id or org_id or district_id:
            serializer = LearningCircleMainSerializer(all_circles, many=True)
        else:
            random_circles = all_circles.order_by('?')[:9]
            serializer = LearningCircleMainSerializer(random_circles, many=True)
        return CustomResponse(response=serializer.data).get_success_response()

class LearningCircleDataAPI(APIView):
    def get(self, request):
        all_circles = LearningCircle.objects.all()
        serializer = LearningCircleDataSerializer(all_circles, many=False)
        return CustomResponse(response=serializer.data).get_success_response()