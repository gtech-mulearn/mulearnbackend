from datetime import datetime, timedelta, timezone
import requests
from rest_framework.views import APIView
from db.learning_circle import LearningCircle, CircleMeetingLog, CircleMeetingAttendees
from db.user import UserInterests
from utils.karma import add_karma
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import Lc
from utils.utils import DateTimeUtils, generate_code
from .learningcircle_serializer import (
    CircleMeetingLogCreateEditSerializer,
    CircleMeetingLogListSerializer,
    CircleMeetupInfoSerializer,
    CircleMeetupMinSerializer,
    LearningCircleCreateEditSerialzier,
    LearningCircleDetailSerializer,
    LearningCircleListMinSerializer,
)
from django.db.models import Q


class LearningCircleView(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, circle_id: str = None):
        if circle_id:
            learning_circle = LearningCircle.objects.get(id=circle_id)
            # circle_meetings = CircleMeetingLog.objects.filter(
            #     circle_id=learning_circle, is_report_submitted=True
            # )
            serializer = LearningCircleDetailSerializer(learning_circle)
            # meetings_serializer = CircleMeetingLogListSerializer(
            #     circle_meetings, many=True
            # )
            return CustomResponse(
                general_message="Learning Circle fetched successfully",
                response={**serializer.data},
            ).get_success_response()
        learning_circles = (
            LearningCircle.objects.all()
            .order_by("-created_at", "-updated_at")
            .select_related("ig", "org", "created_by")
        )
        serializer = LearningCircleListMinSerializer(learning_circles, many=True)
        return CustomResponse(
            general_message="Learning Circles fetched successfully",
            response=serializer.data,
        ).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = LearningCircleCreateEditSerialzier(
            data=request.data, context={"user_id": user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Learning Circle creation failed",
                response=serializer.errors,
            ).get_failure_response()
        result = serializer.save()
        add_karma(
            user_id, Lc.MEET_CREATE_HASHTAG.value, user_id, Lc.MEET_CREATE_KARMA.value
        )
        return CustomResponse(
            general_message="Learning Circle created successfully",
            response={"circle_id": result.id},
        ).get_success_response()

    def put(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle = LearningCircle.objects.get(id=circle_id)
        if learning_circle.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to edit this Learning Circle"
            ).get_failure_response()
        serializer = LearningCircleCreateEditSerialzier(
            learning_circle,
            data=request.data,
            context={"user_id": user_id},
            partial=True,
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Learning Circle update failed",
                response=serializer.errors,
            ).get_failure_response()
        serializer.update(learning_circle, serializer.validated_data)
        return CustomResponse(
            general_message="Learning Circle updated successfully"
        ).get_success_response()

    def delete(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        learning_circle = LearningCircle.objects.get(id=circle_id)
        if learning_circle.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to delete this Learning Circle"
            ).get_failure_response()
        learning_circle.delete()
        return CustomResponse(
            general_message="Learning Circle deleted successfully"
        ).get_success_response()


class LearningCircleMeetingInfoAPI(APIView):
    def get(self, request, meet_id: str):
        user_id = None
        if JWTUtils.is_jwt_authenticated(request):
            user_id = JWTUtils.fetch_user_id(request)
        meet = CircleMeetingLog.objects.get(id=meet_id)
        serializer = CircleMeetupInfoSerializer(meet, context={"user_id": user_id})
        return CustomResponse(
            general_message="Meeting fetched successfully",
            response=serializer.data,
        ).get_success_response()


class LearningCircleMeetingView(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, circle_id: str):
        learning_circle = LearningCircle.objects.get(id=circle_id)
        circle_meetings = CircleMeetingLog.objects.filter(circle_id=learning_circle)
        serializer = CircleMeetupMinSerializer(circle_meetings, many=True)
        return CustomResponse(
            general_message="Circle Meetings fetched successfully",
            response=serializer.data,
        ).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        meet_code = generate_code()
        serializer = CircleMeetingLogCreateEditSerializer(
            data=request.data, context={"user_id": user_id, "meet_code": meet_code}
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Circle Meeting creation failed",
                response=serializer.errors,
            ).get_failure_response()
        serializer.save()
        return CustomResponse(
            general_message="Circle Meeting created successfully"
        ).get_success_response()

    def put(self, request, meet_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        if circle_meeting.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to edit this Circle Meeting"
            ).get_failure_response()
        serializer = CircleMeetingLogCreateEditSerializer(
            circle_meeting,
            data=request.data,
            context={"user_id": user_id},
            partial=True,
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Circle Meeting update failed",
                response=serializer.errors,
            ).get_failure_response()
        serializer.update(circle_meeting, serializer.validated_data)
        return CustomResponse(
            general_message="Circle Meeting updated successfully"
        ).get_success_response()

    def delete(self, request, meet_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.select_related(
            "created_by", "circle_id"
        ).get(id=meet_id)
        if circle_meeting.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to delete this Circle Meeting"
            ).get_failure_response()
        circle_meeting.delete()
        return CustomResponse(
            general_message="Circle Meeting deleted successfully"
        ).get_success_response()


class LearningCircleRSVPAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, meet_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        is_meet_started = (
            circle_meeting.meet_time <= DateTimeUtils.get_current_utc_time()
        )
        is_meet_ended = (
            circle_meeting.meet_time + timedelta(hours=circle_meeting.duration + 2)
        ) <= DateTimeUtils.get_current_utc_time()
        if is_meet_started or is_meet_ended:
            return CustomResponse(
                general_message="Meeting has already started or ended"
            ).get_failure_response()
        attendee = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, user_id_id=user_id
        ).first()
        if attendee:
            return CustomResponse(
                general_message="You have already RSVP'd for the Circle Meeting"
            ).get_failure_response()
        CircleMeetingAttendees.objects.create(
            meet_id=circle_meeting,
            user_id_id=user_id,
            is_joined=False,
            joined_at=None,
        )
        return CustomResponse(
            general_message="You have successfully RSVP'd for the Circle Meeting"
        ).get_success_response()


class LearningCircleJoinAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, meet_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        is_meet_started = (
            circle_meeting.meet_time <= DateTimeUtils.get_current_utc_time()
        )
        if not is_meet_started:
            return CustomResponse(
                general_message="You can only join the Circle Meeting after it has started"
            ).get_failure_response()
        is_meet_ended = (
            circle_meeting.meet_time + timedelta(hours=circle_meeting.duration + 2)
        ) <= DateTimeUtils.get_current_utc_time()
        if is_meet_ended:
            return CustomResponse(
                general_message="The Circle Meeting has already ended"
            ).get_failure_response()

        meet_code = request.data.get("meet_code")

        if not meet_code or meet_code != circle_meeting.meet_code:
            return CustomResponse(
                general_message="Invalid Circle Meeting code"
            ).get_failure_response()

        is_joined = True
        joined_at = DateTimeUtils.get_current_utc_time()
        attendee = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, user_id_id=user_id
        ).first()

        if attendee:
            if attendee.is_joined:
                return CustomResponse(
                    general_message="You have already joined the Circle Meeting"
                ).get_failure_response()
            attendee.is_joined = is_joined
            attendee.joined_at = joined_at
            attendee.save()
        else:
            CircleMeetingAttendees.objects.create(
                meet_id=circle_meeting,
                user_id_id=user_id,
                is_joined=is_joined,
                joined_at=joined_at,
            )
            return CustomResponse(
                general_message="You have successfully joined the Circle Meeting"
            ).get_success_response()
        add_karma(
            user_id, Lc.MEET_JOIN_HASHTAG.value, user_id, Lc.MEET_JOIN_KARMA.value
        )
        return CustomResponse(
            general_message=("You have successfully joined the Circle Meeting")
        ).get_success_response()

    def delete(self, request, meet_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        attendee = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, user_id_id=user_id
        ).first()
        if not attendee:
            return CustomResponse(
                general_message="You have not joined the Circle Meeting"
            ).get_failure_response()
        if attendee.is_report_submitted:
            return CustomResponse(
                general_message="You have already submitted the report"
            ).get_failure_response()
        attendee.delete()
        return CustomResponse(
            general_message=("Removed for meetup attendee list.")
        ).get_success_response()


class LearningCircleAttendeeReportAPI(APIView):
    def get(self, request, meet_id):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        attendee = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, user_id_id=user_id
        ).first()
        if not attendee or not attendee.is_joined:
            return CustomResponse(
                general_message="You have not joined the Circle Meeting"
            ).get_failure_response()
        if not attendee.is_report_submitted:
            return CustomResponse(
                general_message="You have not submitted the report"
            ).get_failure_response()
        return CustomResponse(
            general_message="Report fetched successfully",
            response={
                "report": attendee.report_text,
                "report_link": attendee.report_link,
            },
        ).get_success_response()

    def post(self, request, meet_id):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        attendee = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, user_id_id=user_id
        ).first()
        if not attendee or not attendee.is_joined:
            return CustomResponse(
                general_message="You have not joined the Circle Meeting"
            ).get_failure_response()
        if attendee.is_report_submitted:
            return CustomResponse(
                general_message="You have already submitted the report"
            ).get_failure_response()
        report = request.data.get("report")
        report_link = request.data.get("report_link")
        if not report and not report_link:
            return CustomResponse(
                general_message="Please provide the report or report link"
            ).get_failure_response()
        attendee.is_report_submitted = True
        attendee.report_text = report
        attendee.report_link = report_link
        attendee.save()
        add_karma(
            user_id,
            Lc.ATTENDEE_REPORT_SUBMIT_HASHTAG.value,
            user_id,
            Lc.ATTENDEE_REPORT_SUBMIT_KARMA.value,
        )
        return CustomResponse(
            general_message="You have successfully submitted the report"
        ).get_success_response()

    def delete(self, request, meet_id):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        attendee = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, user_id_id=user_id
        ).first()
        if not attendee or not attendee.is_joined:
            return CustomResponse(
                general_message="You have not joined the Circle Meeting"
            ).get_failure_response()
        if not attendee.is_report_submitted:
            return CustomResponse(
                general_message="You have not submitted the report"
            ).get_failure_response()
        if circle_meeting.is_report_submitted:
            return CustomResponse(
                general_message="The report has already been submitted by the Circle Meeting organizer"
            ).get_failure_response()
        attendee.is_report_submitted = False
        attendee.report_text = None
        attendee.report_link = None
        attendee.save()
        return CustomResponse(
            general_message="You have successfully deleted the report"
        ).get_success_response()


class LearningCircleReportAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, meet_id):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        if circle_meeting.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to view the report"
            ).get_failure_response()
        attendees = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, is_joined=True
        ).select_related("user_id")
        return CustomResponse(
            general_message="Report fetched successfully",
            response={
                "is_report_submitted": circle_meeting.is_report_submitted,
                "report": circle_meeting.report_text,
                "attendees": [
                    {
                        "user_id": attendee.user_id_id,
                        "full_name": attendee.user_id.full_name,
                        "muid": attendee.user_id.muid,
                        "is_lc_approved": attendee.is_lc_approved,
                        "report": attendee.report_text,
                        "report_link": attendee.report_link,
                    }
                    for attendee in attendees
                ],
            },
        ).get_success_response()

    def post(self, request, meet_id):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        if circle_meeting.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to submit the report"
            ).get_failure_response()
        if circle_meeting.is_report_submitted:
            return CustomResponse(
                general_message="The report has already been submitted"
            ).get_failure_response()
        attendees = request.data.get("attendees")
        if not attendees or len(attendees) < 2:
            return CustomResponse(
                general_message="Need minimum of 2 attendees."
            ).get_failure_response()
        report = request.data.get("report")
        if not report:
            return CustomResponse(
                general_message="Please provide the report"
            ).get_failure_response()
        karma_user_ids = []
        for attendee_id, approved in attendees.items():
            attendee = CircleMeetingAttendees.objects.filter(
                meet_id=circle_meeting, user_id_id=attendee_id
            ).first()
            if not attendee or not attendee.is_joined:
                return CustomResponse(
                    general_message="Attendee has not joined the Circle Meeting"
                ).get_failure_response()
            if not attendee.is_report_submitted:
                return CustomResponse(
                    general_message="Attendee has not submitted the report"
                ).get_failure_response()
            attendee.is_lc_approved = approved
            attendee.save()
            if attendee.is_lc_approved:
                karma_user_ids.append(attendee_id)
        circle_meeting.is_report_submitted = True
        circle_meeting.report_text = report
        circle_meeting.save()
        add_karma(
            karma_user_ids,
            Lc.LC_REPORT_HASHTAG.value,
            user_id,
            Lc.LC_REPORT_KARMA.value,
        )
        return CustomResponse(
            general_message="The report has been submitted successfully"
        ).get_success_response()

    def delete(self, request, meet_id):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        if circle_meeting.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to delete the report"
            ).get_failure_response()
        if not circle_meeting.is_report_submitted:
            return CustomResponse(
                general_message="The report has not been submitted"
            ).get_failure_response()
        if circle_meeting.is_approved:
            return CustomResponse(
                general_message="The report has been approved by the Learning Circle organizer"
            ).get_failure_response()
        attendees = CircleMeetingAttendees.objects.filter(
            meet_id=circle_meeting, is_joined=True
        )
        for attendee in attendees:
            attendee.is_lc_approved = False
            attendee.save()
        circle_meeting.is_report_submitted = False
        circle_meeting.report_text = None
        circle_meeting.save()
        return CustomResponse(
            general_message="The report has been deleted successfully"
        ).get_success_response()


class LearningCircleMeetingListAPI(APIView):

    def get(self, request):
        request_data = request.query_params
        category = request_data.get("category", None)
        saved = request_data.get("saved", "0")
        participated = request_data.get("participated", "0")
        saved = str(saved).lower() in ("true", "1")
        participated = str(participated).lower() in ("true", "1")
        # no_location = request_data.get("no_location")
        lat = request_data.get("lat")
        lon = request_data.get("lon")
        user_id = None
        if JWTUtils.is_jwt_authenticated(request):
            user_id = JWTUtils.fetch_user_id(request)
        if saved or participated:
            if not user_id:
                return CustomResponse(
                    general_message="User not authenticated"
                ).get_failure_response()
            category = "all"
        if saved and participated:
            return CustomResponse(
                general_message="Please provide either saved or participated"
            ).get_failure_response()
        if user_id and not category and category != "all":
            user_id = JWTUtils.fetch_user_id(request)
            interests = UserInterests.objects.filter(user_id=user_id).first()
            if interests:
                category = interests.choosen_interests
        if category != "all" and type(category) == str:
            category = [category]
        # if not no_location and not lat and not lon:
        #     user_ip = request.META.get("REMOTE_ADDR")
        #     ipinfo_api_url = f"http://ip-api.com/json/{user_ip}?fields=status,lat,lon"
        #     response = requests.get(ipinfo_api_url)
        #     location_data = response.json()
        #     if location_data.get("status") == "success":
        #         lat = location_data.get("lat")
        #         lon = location_data.get("lon")
        if saved:
            filter = Q(user_id=user_id, is_joined=False)
        elif participated:
            filter = Q(user_id=user_id, is_joined=True)
        else:
            filter = Q(user_id=user_id, is_report_submitted=False)
        user_meetups = (
            []
            if not user_id
            else CircleMeetingAttendees.objects.filter(filter).values_list(
                "meet_id_id", flat=True
            )
        )
        if saved or participated:
            filter = Q(id__in=user_meetups)
        else:
            filter = Q(
                meet_time__gte=DateTimeUtils.get_current_utc_time() - timedelta(hours=2)
            ) | Q(id__in=user_meetups)
        meetings = (
            CircleMeetingLog.objects.filter(filter).order_by("meet_time")
            # .prefetch_related("circle_meeting_attendance_meet_id")
        )
        if category and category != "all" and type(category) == list:
            meetings = meetings.select_related("circle_id__ig").filter(
                circle_id__ig__category__in=category
            )
        serializer = CircleMeetupMinSerializer(
            meetings, many=True, context={"user_id": user_id}
        )
        return CustomResponse(
            general_message="Meetings fetched successfully",
            response=serializer.data,
        ).get_success_response()
