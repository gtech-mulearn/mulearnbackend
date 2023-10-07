from decouple import config
from django.core.mail import send_mail
from django.db.models import Q
from rest_framework.views import APIView

from api.notification.notifications_utils import NotificationUtils
from db.learning_circle import LearningCircle, UserCircleLink
from db.user import User
from utils.permission import JWTUtils
from utils.response import CustomResponse
from .dash_lc_serializer import LearningCircleSerializer, LearningCircleCreateSerializer, LearningCircleHomeSerializer, \
    LearningCircleUpdateSerializer, LearningCircleJoinSerializer, LearningCircleMeetSerializer, \
    LearningCircleMainSerializer, LearningCircleNoteSerializer, LearningCircleDataSerializer, \
    LearningCircleMemberlistSerializer

domain = config("FR_DOMAIN_NAME")
from_mail = config("FROM_MAIL")


class TotalLearningCircleListApi(APIView):
    def post(self, request, circle_code=None):
        user_id = JWTUtils.fetch_user_id(request)
        filters = Q()

        filters &= ~Q(usercirclelink__accepted=1, usercirclelink__user_id=user_id)
        if district_id := request.data.get('district_id'):
            filters &= Q(org__district_id=district_id)
        if org_id := request.data.get('org_id'):
            filters &= Q(org_id=org_id)
        if interest_group_id := request.data.get('ig_id'):
            filters &= Q(ig_id=interest_group_id)

        if circle_code:
            if not LearningCircle.objects.filter(Q(circle_code=circle_code) | Q(name__icontains=circle_code)).exists():
                return CustomResponse(general_message='invalid circle code or Circle Name').get_failure_response()
            filters &= Q(circle_code=circle_code) | Q(name__icontains=circle_code)

        learning_queryset = LearningCircle.objects.filter(filters)
        learning_serializer = LearningCircleSerializer(learning_queryset, many=True)

        return CustomResponse(response=learning_serializer.data).get_success_response()


class LearningCircleCreateApi(APIView):
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
            user = User.objects.filter(id=lc.user.id).first()
            NotificationUtils.insert_notification(user=user,
                                                  title="Member Request",
                                                  description=f"{full_name} has requested to join your learning circle",
                                                  button="LC",
                                                  url=f'{domain}/api/v1/dashboard/lc/{circle_id}/{user_id}/',
                                                  created_by=user)
            return CustomResponse(general_message='Request sent').get_success_response()
        return CustomResponse(message=serializer.errors).get_failure_response()


class UserLearningCircleListApi(APIView):
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


class LearningCircleLeadTransfer(APIView):
    def patch(self, request, circle_id, lead_id):
        user_id = JWTUtils.fetch_user_id(request)
        usr_circle_link = UserCircleLink.objects.filter(circle__id=circle_id, user__id=user_id).first()
        lead_circle_link = UserCircleLink.objects.filter(circle__id=circle_id, user__id=lead_id).first()
        if not LearningCircle.objects.filter(id=circle_id).exists():
            return CustomResponse(general_message='Learning Circle not found').get_failure_response()
        if usr_circle_link is None or usr_circle_link.lead != 1:
            return CustomResponse(general_message='User is not lead').get_failure_response()
        if lead_circle_link is None:
            return CustomResponse(general_message='New lead not found in the circle').get_failure_response()
        usr_circle_link.lead = None
        lead_circle_link.lead = 1
        usr_circle_link.save()
        lead_circle_link.save()
        return CustomResponse(general_message='Lead transferred successfully').get_success_response()


class LearningCircleHomeApi(APIView):
    def get(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleHomeSerializer(learning_circle, many=False, context={"user_id": user_id})
        return CustomResponse(response=serializer.data).get_success_response()

    def post(self, request, member_id, circle_id):
        learning_circle_link = UserCircleLink.objects.filter(user_id=member_id, circle_id=circle_id).first()
        if learning_circle_link is None:
            return CustomResponse(general_message='User not part of circle').get_failure_response()
        serializer = LearningCircleUpdateSerializer()
        serializer.destroy(learning_circle_link)
        return CustomResponse(general_message='Removed successfully').get_success_response()

    def patch(self, request, member_id, circle_id):
        user_id = JWTUtils.fetch_user_id(request)

        if not UserCircleLink.objects.filter(user_id=member_id,
                                             circle_id=circle_id).exists() or not LearningCircle.objects.filter(
            id=circle_id).exists():
            return CustomResponse(general_message='Learning Circle Not Available').get_failure_response()

        learning_circle_link = UserCircleLink.objects.filter(user_id=member_id, circle_id=circle_id).first()
        if learning_circle_link.accepted is not None:
            return CustomResponse(general_message='Already evaluated').get_failure_response()

        serializer = LearningCircleUpdateSerializer(learning_circle_link, data=request.data,
                                                    context={'user_id': user_id})
        if serializer.is_valid():
            serializer.save()
            is_accepted = request.data.get('is_accepted')
            user = User.objects.filter(id=member_id).first()
            if is_accepted == '1':

                NotificationUtils.insert_notification(user, title="Request approved",
                                                      description="You request to join the learning circle has been approved",
                                                      button="LC",
                                                      url=f'{domain}/api/v1/dashboard/lc/{circle_id}/',
                                                      created_by=User.objects.filter(id=user_id).first())
            else:
                NotificationUtils.insert_notification(user, title="Request rejected",
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
            return CustomResponse(general_message='User not part of circle').get_failure_response()

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
            if learning_circle := LearningCircle.objects.filter(
                    id=circle_id
            ).first():
                learning_circle.delete()
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


class LearningCircleListMembersApi(APIView):
    def get(self, request, circle_name):
        lc = LearningCircle.objects.filter(name=circle_name)
        if lc is None:
            return CustomResponse(general_message='Learning Circle Not Exists').get_failure_response()
        serializer = LearningCircleMemberlistSerializer(lc, many=True)
        return CustomResponse(response=serializer.data).get_success_response()


class LearningCircleInviteLeadAPI(APIView):

    def post(self, request):
        circle_id = request.POST.get('lc')
        muid = request.POST.get('muid')
        user_id = JWTUtils.fetch_user_id(request)
        usr_circle_link = UserCircleLink.objects.filter(circle__id=circle_id, user__id=user_id).first()
        if not usr_circle_link:
            return CustomResponse(general_message='User not part of circle').get_failure_response()
        if usr_circle_link.lead:
            user = User.objects.filter(muid=muid).first()
            if not user:
                return CustomResponse(general_message='Muid is Invalid').get_failure_response()
            # send_template_mail(
            #     context=user,
            #     subject="LC µFAM IS HERE!",
            #     address=["user_registration.html"],
            # )
            send_mail(
                "LC Invite",
                "Join our lc",
                from_mail,
                [user.email],
                fail_silently=False,
            )
            return CustomResponse(general_message='User Invited').get_success_response()
