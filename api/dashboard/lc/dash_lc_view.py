import uuid

from decouple import config
from django.core.mail import send_mail
from django.db.models import Q, F, Value, CharField
from django.db.models.functions import Concat
from django.shortcuts import redirect
from rest_framework.views import APIView


from api.notification.notifications_utils import NotificationUtils
from db.learning_circle import LearningCircle, UserCircleLink, CircleMeetingLog
from db.user import User
from db.task import TaskList
from utils.permission import JWTUtils
from utils.response import CustomResponse
from utils.utils import send_template_mail, DateTimeUtils
from .dash_lc_serializer import LearningCircleSerializer, LearningCircleCreateSerializer, LearningCircleDetailsSerializer, \
    LearningCircleUpdateSerializer, LearningCircleJoinSerializer, \
    LearningCircleMainSerializer, LearningCircleNoteSerializer, LearningCircleDataSerializer, \
    LearningCircleMemberListSerializer, MeetRecordsCreateEditDeleteSerializer, IgTaskDetailsSerializer, \
    ScheduleMeetingSerializer, ListAllMeetRecordsSerializer, AddMemberSerializer

from .dash_ig_helper import is_learning_circle_member, is_valid_learning_circle, get_today_start_end, get_week_start_end

domain = config("FR_DOMAIN_NAME")
from_mail = config("FROM_MAIL")


class UserLearningCircleListApi(APIView):
    """
    API endpoint for listing a user's learning circles.

    Endpoint: /api/v1/dashboard/lc/ (GET)

    Returns:
        CustomResponse: A custom response containing a list of learning circles
        associated with the user.
    """

    def get(self, request):  # Lists user's learning circle
        user_id = JWTUtils.fetch_user_id(request)

        learning_queryset = LearningCircle.objects.filter(
            user_circle_link_circle__user_id=user_id,
            user_circle_link_circle__accepted=1
        )

        learning_serializer = LearningCircleSerializer(
            learning_queryset,
            many=True
        )

        return CustomResponse(
            response=learning_serializer.data
        ).get_success_response()


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
            serializer = LearningCircleMainSerializer(
                all_circles,
                many=True
            )
        else:
            random_circles = all_circles.order_by('?')[:9]

            serializer = LearningCircleMainSerializer(
                random_circles,
                many=True
            )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()


class LearningCircleDataAPI(APIView):
    """
        API endpoint for retrieving basic data about all learning circles.

        Endpoint: /api/v1/dashboard/lc/data/ (GET)

        Returns:
            CustomResponse: A custom response containing data about all learning circles.
        """

    def get(self, request):
        learning_circle = LearningCircle.objects.all()

        serializer = LearningCircleDataSerializer(
            learning_circle,
            many=False
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()


class LearningCircleCreateApi(APIView):
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = LearningCircleCreateSerializer(
            data=request.data,
            context={
                'user_id': user_id
            }
        )
        if serializer.is_valid():
            circle = serializer.save()

            return CustomResponse(
                general_message='LearningCircle created successfully',
                response={
                    'circle_id': circle.id
                }
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()


class LearningCircleListMembersApi(APIView):
    def get(self, request, circle_id):
        # learning_circle = LearningCircle.objects.filter(
        #     id=circle_id
        # )
        user_learning_circle = UserCircleLink.objects.filter(
            circle_id=circle_id
        )

        if user_learning_circle is None:
            return CustomResponse(
                general_message='Learning Circle Not Exists'
            ).get_failure_response()

        serializer = LearningCircleMemberListSerializer(
            user_learning_circle,
            many=True,
            context={
                'circle_id': circle_id
            }
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()


class TotalLearningCircleListApi(APIView):
    def post(self, request, circle_code=None):
        user_id = JWTUtils.fetch_user_id(request)
        filters = Q()

        filters &= ~Q(
            user_circle_link_circle__accepted=1,
            user_circle_link_circle__user_id=user_id
        )

        if district_id := request.data.get('district_id'):
            filters &= Q(
                org__district_id=district_id
            )
        if org_id := request.data.get('org_id'):
            filters &= Q(org_id=org_id)
        if interest_group_id := request.data.get('ig_id'):
            filters &= Q(ig_id=interest_group_id)

        if circle_code:
            if not LearningCircle.objects.filter(
                    Q(circle_code=circle_code) |
                    Q(name__icontains=circle_code)
            ).exists():

                return CustomResponse(
                    general_message='invalid circle code or Circle Name'
                ).get_failure_response()

            filters &= (
                    Q(circle_code=circle_code) |
                    Q(name__icontains=circle_code)
            )

        learning_queryset = LearningCircle.objects.filter(
            filters
        )

        learning_serializer = LearningCircleSerializer(
            learning_queryset,
            many=True
        )

        return CustomResponse(
            response=learning_serializer.data
        ).get_success_response()


class LearningCircleJoinApi(APIView):
    def post(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)

        user = User.objects.filter(id=user_id).first()

        full_name = f'{user.fullname}'
        serializer = LearningCircleJoinSerializer(
            data=request.data,
            context={
                'user_id': user_id,
                'circle_id': circle_id
            }
        )
        if serializer.is_valid():
            serializer.save()
            lead = UserCircleLink.objects.filter(circle_id=circle_id, lead=True).first()
            NotificationUtils.insert_notification(
                user=lead.user,
                title="Member Request",
                description=f"{full_name} has requested to join your learning circle",
                button="LC",
                url=f'{domain}/api/v1/dashboard/lc/{circle_id}/{user_id}/',
                created_by=user
            )

            return CustomResponse(
                general_message='Request sent'
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()


class LearningCircleDetailsApi(APIView):
    def get(self, request, circle_id, member_id=None):
        user_id = JWTUtils.fetch_user_id(request)

        if not is_valid_learning_circle(circle_id):
            return CustomResponse(
                general_message='invalid learning circle'
            ).get_failure_response()

        if not is_learning_circle_member(user_id, circle_id):
            return CustomResponse(
                general_message='unauthorized access'
            ).get_failure_response()

        learning_circle = LearningCircle.objects.filter(
            id=circle_id
        ).first()

        serializer = LearningCircleDetailsSerializer(
            learning_circle,
            many=False,
            context={
                "user_id": user_id,
                "circle_id": circle_id
            }
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()

    def post(self, request, member_id, circle_id):

        learning_circle_link = UserCircleLink.objects.filter(
            user_id=member_id,
            circle_id=circle_id
        ).first()

        if learning_circle_link is None:
            return CustomResponse(
                general_message='User not part of circle'
            ).get_failure_response()

        serializer = LearningCircleUpdateSerializer()
        serializer.destroy(learning_circle_link)

        return CustomResponse(
            general_message='Removed successfully'
        ).get_success_response()

    def patch(self, request, member_id, circle_id):
        user_id = JWTUtils.fetch_user_id(request)

        if not UserCircleLink.objects.filter(
                user_id=member_id,
                circle_id=circle_id
        ).exists() or not LearningCircle.objects.filter(
            id=circle_id
        ).exists():

            return CustomResponse(
                general_message='Learning Circle Not Available'
            ).get_failure_response()

        learning_circle_link = UserCircleLink.objects.filter(
            user_id=member_id,
            circle_id=circle_id
        ).first()

        if learning_circle_link.accepted is not None:
            return CustomResponse(
                general_message='Already evaluated'
            ).get_failure_response()

        serializer = LearningCircleUpdateSerializer(
            learning_circle_link,
            data=request.data,
            context={
                'user_id': user_id
            }
        )

        if serializer.is_valid():
            serializer.save()
            is_accepted = request.data.get('is_accepted')
            user = User.objects.filter(id=member_id).first()

            if is_accepted == '1':
                NotificationUtils.insert_notification(
                    user, title="Request approved",
                    description="You request to join the learning circle has been approved",
                    button="LC",
                    url=f'{domain}/api/v1/dashboard/lc/{circle_id}/',
                    created_by=User.objects.filter(id=user_id).first())
            else:
                NotificationUtils.insert_notification(
                    user, title="Request rejected",
                    description="You request to join the learning circle has been rejected",
                    button="LC",
                    url=f'{domain}/api/v1/dashboard/lc/join',
                    created_by=User.objects.filter(id=user_id).first())

            return CustomResponse(
                general_message='Approved successfully'
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    def put(self, request, circle_id):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        serializer = LearningCircleNoteSerializer(learning_circle, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return CustomResponse(
                general_message='Note updated successfully').get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

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


class SingleReportDetailAPI(APIView):

    def get(self, request, circle_id, report_id=None):
        circle_meeting_log = CircleMeetingLog.objects.get(id=report_id)

        serializer = MeetRecordsCreateEditDeleteSerializer(
            circle_meeting_log,
            many=False
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()

    def post(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)
        time = request.data.get('time')

        serializer = MeetRecordsCreateEditDeleteSerializer(
            data=request.data,
            context={
                'user_id': user_id,
                'circle_id': circle_id,
                'time': time
            }
        )
        if serializer.is_valid():
            circle_meet_log = serializer.save()

            return CustomResponse(
                general_message=f'Meet scheduled at {circle_meet_log.meet_time}'
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()

    # def patch(self, request, circle_id):
    #     user_id = JWTUtils.fetch_user_id(request)
    #
    #     learning_circle = LearningCircle.objects.filter(
    #         id=circle_id
    #     ).first()
    #
    #     serializer = MeetRecordsCreateEditDeleteSerializer(
    #         learning_circle,
    #         data=request.data,
    #         context={
    #             'user_id': user_id
    #         }
    #     )
    #     if serializer.is_valid():
    #         serializer.save()
    #
    #         return CustomResponse(
    #             general_message='Meet updated successfully'
    #         ).get_success_response()
    #
    #     return CustomResponse(
    #         message=serializer.errors
    #     ).get_failure_response()


class LearningCircleLeadTransfer(APIView):
    def patch(self, request, circle_id, new_lead_id):
        user_id = JWTUtils.fetch_user_id(request)

        user_circle_link = UserCircleLink.objects.filter(
            circle__id=circle_id,
            user__id=user_id
        ).first()

        new_lead_circle_link = UserCircleLink.objects.filter(
            circle__id=circle_id,
            user__id=new_lead_id
        ).first()

        if not LearningCircle.objects.filter(
                id=circle_id
        ).exists():
            return CustomResponse(
                general_message='Learning Circle not found'
            ).get_failure_response()

        if user_circle_link is None or user_circle_link.lead != 1:
            return CustomResponse(
                general_message='User is not lead'
            ).get_failure_response()

        if new_lead_circle_link is None:
            return CustomResponse(
                general_message='New lead not found in the circle'
            ).get_failure_response()

        user_circle_link.lead = None
        new_lead_circle_link.lead = 1
        user_circle_link.save()
        new_lead_circle_link.save()

        return CustomResponse(
            general_message='Lead transferred successfully'
        ).get_success_response()


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


class LearningCircleInviteMemberAPI(APIView):
    """
    Invite a member to a learning circle.
    """

    def post(self, request, circle_id, muid):
        """
        POST request to invite a member to a learning circle.
        :param request: Request object.
        :param circle_id: Learning circle id.
        :param muid: Muid of the user.
        """
        user = User.objects.filter(muid=muid).first()
        if not user:
            return CustomResponse(
                general_message='Muid is Invalid'
            ).get_failure_response()

        user_circle_link = UserCircleLink.objects.filter(
            circle__id=circle_id,
            user__id=user.id
        ).first()

        if user_circle_link:
            if user_circle_link.accepted:

                return CustomResponse(
                    general_message='User already part of circle'
                ).get_failure_response()

            elif user_circle_link.is_invited:
                return CustomResponse(
                    general_message='User already invited'
                ).get_failure_response()

        receiver_email = user.email
        html_address = ["lc_invitation.html"]
        inviter = User.objects.filter(id=JWTUtils.fetch_user_id(request)).first()
        inviter_name = inviter.full_name
        context = {
            "circle_name": LearningCircle.objects.filter(
                id=circle_id
            ).first().name,
            "inviter_name": inviter_name,
            "circle_id": circle_id,
            "muid": muid,
            "email": receiver_email,
        }
        status = send_template_mail(
            context=context,
            subject="MuLearn - Invitation to learning circle",
            address=html_address,
        )

        if status == 1:
            UserCircleLink.objects.create(
                id=uuid.uuid4(),
                circle_id=circle_id,
                user=user,
                is_invited=True,
                accepted=False,
                created_at=DateTimeUtils.get_current_utc_time(),
            )

            return CustomResponse(
                general_message='User Invited'
            ).get_success_response()

        return CustomResponse(
            general_message='Mail not sent'
        ).get_failure_response()


class LearningCircleInvitationStatus(APIView):
    """
    API to update the invitation status
    """

    def post(self, request, circle_id, muid, status):
        """
        PUT request to accept the invitation to join the learning circle, by adding the user data to the lc
        :param request: Request object.
        :param muid: Muid of the user.
        :param circle_id: Learning circle id.
        :param status: Status of the invitation.
        """
        user = User.objects.filter(muid=muid).first()
        if not user:
            return CustomResponse(
                general_message='Muid is Invalid'
            ).get_failure_response()

        user_circle_link = UserCircleLink.objects.filter(
            circle__id=circle_id,
            user__id=user.id
        ).first()

        if not user_circle_link:
            return CustomResponse(
                general_message='User not invited'
            ).get_failure_response()

        if status == "accepted":
            user_circle_link.accepted = True
            user_circle_link.accepted_at = DateTimeUtils.get_current_utc_time()
            user_circle_link.save()
            # return CustomResponse(general_message='User added to circle').get_success_response()
            return redirect(f'{domain}/dashboard/learning-circle/')

        elif status == "rejected":
            user_circle_link.delete()

            return CustomResponse(
                general_message='User rejected invitation'
            ).get_failure_response()


class ScheduleMeetAPI(APIView):
    def put(self, request, circle_id):
        learning_circle = LearningCircle.objects.filter(
            id=circle_id
        ).first()

        serializer = ScheduleMeetingSerializer(
            learning_circle,
            data=request.data
        )
        if serializer.is_valid():
            data = serializer.save()

            return CustomResponse(
                general_message=f"meet scheduled on {data.meet_time}"
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()


class IgTaskDetailsAPI(APIView):
    def get(self, request, circle_id):
        task_list = TaskList.objects.filter(ig__learning_circle_ig__id=circle_id)

        serializer = IgTaskDetailsSerializer(
            task_list,
            many=True,
        )

        return CustomResponse(
            response=serializer.data
        ).get_success_response()


class AddMemberAPI(APIView):
    def post(self, request, circle_id):
        muid = request.data.get('muid')

        user = User.objects.filter(muid=muid).first()
        if not user:
            return CustomResponse(
                general_message="invalid user"
            ).get_failure_response()

        serializer = AddMemberSerializer(
            data=request.data,
            context={
                'user': user,
                'muid': muid,
                'circle_id': circle_id,
            }
        )
        if serializer.is_valid():
            serializer.save()

            return CustomResponse(
                general_message='user added successfully'
            ).get_success_response()

        return CustomResponse(
            message=serializer.errors
        ).get_failure_response()


class ValidateUserMeetCreateAPI(APIView):
    def get(self, request, circle_id):
        user_id = JWTUtils.fetch_user_id(request)

        if not is_valid_learning_circle(circle_id):
            return CustomResponse(
                general_message='invalid learning circle'
            ).get_failure_response()

        if not is_learning_circle_member(user_id, circle_id):
            return CustomResponse(
                general_message='unauthorized access'
            ).get_failure_response()

        today_date_time = DateTimeUtils.get_current_utc_time()

        start_of_day, end_of_day = get_today_start_end(today_date_time)
        start_of_week, end_of_week = get_week_start_end(today_date_time)

        if CircleMeetingLog.objects.filter(
            circle_id=circle_id,
            meet_time__range=(
                start_of_day,
                end_of_day
            )
        ).exists():
            return CustomResponse(
                general_message=f'Another meet already scheduled on {today_date_time.date()}'
            ).get_failure_response()

        if CircleMeetingLog.objects.filter(
            circle_id=circle_id,
            meet_time__range=(
                start_of_week,
                end_of_week
            )
        ).count() >= 5:
            return CustomResponse(
                general_message='you can create only 5 meeting in a week'
            ).get_failure_response()

        return CustomResponse(
            general_message='success'
        ).get_success_response()
