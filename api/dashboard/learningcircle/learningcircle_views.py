from datetime import timedelta
import uuid

import requests
from django.db import transaction
from django.db.models import Sum, Q
from rest_framework.views import APIView

from db.learning_circle import (
    LearningCircle,
    CircleMeetingLog,
    CircleMeetingAttendees,
    UserCircleLink,
)
from db.task import KarmaActivityLog
from db.user import UserDomains, User
from utils.karma import add_karma, remove_karma
from utils.utils import CommonUtils
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import Lc
from utils.utils import DateTimeUtils, generate_code
from .learningcircle_serializer import (
    CircleMeetingLogCreateEditSerializer,
    CircleMeetupInfoSerializer,
    CircleMeetupMinSerializer,
    CircleMeetupPublicSerializer,
    LearningCircleCreateEditSerialzier,
    LearningCircleDetailSerializer,
    LearningCircleListMinSerializer,
)



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

        ig_id = request.query_params.get("ig")
        if ig_id:
            learning_circles = learning_circles.filter(ig_id=ig_id)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            learning_circles,
            request,
            search_fields=["title"],
        )
        serializer = LearningCircleListMinSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated_queryset.get("pagination"),
        )

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
        try:
            learning_circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(
            general_message="Learning Circle not found"
        ).get_failure_response()
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
            
        serializer.save()
    
        return CustomResponse(
            general_message="Learning Circle updated successfully"
        ).get_success_response()

    def delete(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        try:
            learning_circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(
                general_message="Learning Circle not found"
            ).get_failure_response()
        if learning_circle.created_by_id != user_id:
            return CustomResponse(
                general_message="You do not have permission to delete this Learning Circle"
            ).get_failure_response()
        learning_circle.delete()
        return CustomResponse(
            general_message="Learning Circle deleted successfully"
        ).get_success_response()


class LearningCircleMeetingInfoAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, meet_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        meet = CircleMeetingLog.objects.filter(id=meet_id).first()
        if not meet:
            return CustomResponse(
                general_message="Meeting not found"
            ).get_failure_response()
        serializer = CircleMeetupInfoSerializer(meet, context={"user_id": user_id})
        return CustomResponse(
            general_message="Meeting fetched successfully",
            response=serializer.data,
        ).get_success_response()


class LearningCircleMeetingListView(APIView):
    def get(self, request, circle_id: str):
        learning_circle = LearningCircle.objects.filter(id=circle_id).first()
        if not learning_circle:
            return CustomResponse(
                general_message="Learning Circle not found"
            ).get_failure_response()
        circle_meetings = CircleMeetingLog.objects.filter(circle_id=learning_circle)
        serializer = CircleMeetupMinSerializer(circle_meetings, many=True)
        return CustomResponse(
            general_message="Circle Meetings fetched successfully",
            response=serializer.data,
        ).get_success_response()


class LearningCircleMeetingView(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)
        meet_code = generate_code()
        request_data = request.data.copy()
        request_data['circle_id'] = circle_id
        serializer = CircleMeetingLogCreateEditSerializer(
            data=request_data, context={"user_id": user_id, "meet_code": meet_code}
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
        serializer.save()
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
        now = DateTimeUtils.get_current_utc_time()
        if circle_meeting.meet_time <= now:
            return CustomResponse(
                general_message="Meeting has already started"
            ).get_failure_response()
        if (
            circle_meeting.meet_time + timedelta(hours=circle_meeting.duration)
        ) <= now:
            return CustomResponse(
                general_message="Meeting has already ended"
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
        now = DateTimeUtils.get_current_utc_time()
        if circle_meeting.meet_time > now:
            return CustomResponse(
                general_message="You can only join the Circle Meeting after it has started"
            ).get_failure_response()
        is_meet_ended = (
            circle_meeting.meet_time + timedelta(hours=circle_meeting.duration)
        ) <= now
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
    permission_classes = [CustomizePermission]

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
        remove_karma(
            user_id,
            Lc.ATTENDEE_REPORT_SUBMIT_HASHTAG.value,
            Lc.ATTENDEE_REPORT_SUBMIT_KARMA.value,
        )
        return CustomResponse(
            general_message="You have successfully deleted the report"
        ).get_success_response()


class LearningCircleReportAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, meet_id):
        user_id = JWTUtils.fetch_user_id(request)
        circle_meeting = CircleMeetingLog.objects.get(id=meet_id)
        circle = circle_meeting.circle_id
        if circle_meeting.created_by_id != user_id and not _is_lead_or_creator(
            circle, user_id
        ):
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
        karma_user_ids = []
        with transaction.atomic():
            for attendee_id, approved in attendees.items():
                attendee = CircleMeetingAttendees.objects.filter(
                    meet_id=circle_meeting, user_id_id=attendee_id
                ).first()
                attendee.is_lc_approved = approved
                attendee.save()
                if approved:
                    karma_user_ids.append(attendee_id)
            circle_meeting.is_report_submitted = True
            circle_meeting.report_text = report
            circle_meeting.save()
            if karma_user_ids:
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
        karma_user_ids = list(
            attendees.filter(is_lc_approved=True).values_list("user_id_id", flat=True)
        )
        for attendee in attendees:
            attendee.is_lc_approved = False
            attendee.save()
        circle_meeting.is_report_submitted = False
        circle_meeting.report_text = None
        circle_meeting.save()
        if karma_user_ids:
            remove_karma(
                karma_user_ids,
                Lc.LC_REPORT_HASHTAG.value,
                Lc.LC_REPORT_KARMA.value,
            )
        return CustomResponse(
            general_message="The report has been deleted successfully"
        ).get_success_response()


class LearningCircleMeetingPublicListView(APIView):
    def get(self, request):
        request_data = request.query_params
        ig_id = request_data.get("ig_id", None)
        queryset = (
            CircleMeetingLog.objects.select_related("circle_id__ig")
            .all()
            .order_by("-meet_time")
        )
        if ig_id:
            queryset = queryset.filter(circle_id__ig_id=ig_id)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            queryset,
            request,
            search_fields=["title", "description", "circle_id__ig__name"],
        )

        serializer = CircleMeetupPublicSerializer(
            paginated_queryset.get("queryset"), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data, pagination=paginated_queryset.get("pagination")
        )


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
        else:
            return CustomResponse(
                general_message="User not authenticated"
            ).get_failure_response(status_code=401)
        if saved or participated:
            category = "all"
        if saved and participated:
            return CustomResponse(
                general_message="Please provide either saved or participated"
            ).get_failure_response()
        if user_id and not category and category != "all":
            # user_id = JWTUtils.fetch_user_id(request)
            category = UserDomains.objects.filter(user_id=user_id).values_list(
                "domain_name", flat=True
            )

        if category != "all" and isinstance(category, str):
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
            filter = Q()
            # filter = Q(
            #     meet_time__gte=DateTimeUtils.get_current_utc_time() - timedelta(hours=2)
            # ) | Q(id__in=user_meetups)
        meetings = CircleMeetingLog.objects.filter(filter).order_by("meet_time")
        if category and category != "all" and isinstance(category, list):
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




class LearningCircleMemberDetailsView(APIView):
    def get(self, request, circle_id):
        try:
            circle = LearningCircle.objects.select_related('ig', 'created_by').get(id=circle_id)
            
            member_links = UserCircleLink.objects.filter(
                circle=circle_id,
                accepted=True,
            ).select_related('user')
            
            leaders = set(link.user_id for link in member_links if link.lead)
            
            member_ids = [link.user_id for link in member_links]
            
            users = {user.id: user for user in User.objects.filter(id__in=member_ids)}
    
            karma_data = KarmaActivityLog.objects.filter(
                user_id__in=member_ids,
                task__ig=circle.ig
            ).values('user_id').annotate(
                ig_karma=Sum('karma')
            )
            
            karma_by_user = {item['user_id']: item['ig_karma'] for item in karma_data}
            
            member_details = []
          
            for link in member_links:
                user_id = link.user_id
                user = users.get(user_id)
                if not user:
                    continue
                member_details.append({
                    'id': user.id,
                    'full_name': user.full_name,
                    'profile_pic': user.profile_pic,
                    'muid': user.muid,
                    'ig_karma': karma_by_user.get(user.id, 0),
                    'is_leader': user.id in leaders
                })
            
            # Sort by karma (highest first)
            member_details = sorted(member_details, key=lambda x: x['ig_karma'], reverse=True)

            # Build owner details from the circle's created_by FK
            owner = circle.created_by
            owner_details = {
                'id': owner.id,
                'full_name': owner.full_name,
                'profile_pic': owner.profile_pic,
                'muid': owner.muid,
            }
            
            return CustomResponse(
                general_message="Learning Circle member details fetched successfully",
                response={
                    'owner': owner_details,
                    'members': member_details,
                }
            ).get_success_response()
        
        except LearningCircle.DoesNotExist:
            return CustomResponse(
                general_message="Learning Circle not found"
            ).get_failure_response()

# --- New Views ---


def _is_lead_or_creator(circle, user_id):
    """Returns True if the user is the circle creator OR has lead=True in UserCircleLink."""
    if circle.created_by_id == user_id:
        return True
    return UserCircleLink.objects.filter(
        circle=circle, user_id=user_id, accepted=True, lead=True
    ).exists()


class UserCircleListAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        links = (
            UserCircleLink.objects.filter(user_id=user_id, accepted=True)
            .select_related('circle__ig', 'circle__org')
        )
        from .learningcircle_serializer import UserCircleListSerializer
        serializer = UserCircleListSerializer(links, many=True)
        return CustomResponse(
            general_message="User circles fetched successfully",
            response=serializer.data,
        ).get_success_response()


class CircleJoinAPI(APIView):
    """
    POST  — member sends a join request (pending lead approval)
    GET   — lead/creator lists all pending join requests
    PATCH — lead/creator accepts or rejects a pending join request
    """
    permission_classes = [CustomizePermission]

    def post(self, request, circle_id: str):
        """User sends a join request. Creates a pending UserCircleLink (accepted=None)."""
        user_id = JWTUtils.fetch_user_id(request)

        try:
            circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(general_message="Learning Circle not found").get_failure_response()

        existing = UserCircleLink.objects.filter(circle=circle, user_id=user_id).first()

        if existing:
            if existing.accepted is True:
                return CustomResponse(
                    general_message="You are already a member of this circle"
                ).get_failure_response()
            # Accept a pending invite sent by a lead
            if existing.is_invited and existing.accepted is None:
                existing.accepted = True
                existing.accepted_at = DateTimeUtils.get_current_utc_time()
                existing.save()
                return CustomResponse(
                    general_message="Invitation accepted. You have joined the circle."
                ).get_success_response()
            # A pending join request already exists
            if not existing.is_invited and existing.accepted is None:
                return CustomResponse(
                    general_message="Join request already sent. Waiting for lead approval."
                ).get_failure_response()
            # Any other link state (e.g. previously rejected)
            return CustomResponse(
                general_message="You have a previous link to this circle that prevents joining. Contact the circle lead."
            ).get_failure_response()

        UserCircleLink.objects.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            circle=circle,
            lead=False,
            is_invited=False,
            accepted=None,
            accepted_at=None,
        )
        return CustomResponse(
            general_message="Join request sent. Waiting for lead approval."
        ).get_success_response()

    def get(self, request, circle_id: str):
        """Lead/creator lists all pending join requests for this circle."""
        user_id = JWTUtils.fetch_user_id(request)

        try:
            circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(general_message="Learning Circle not found").get_failure_response()

        if not _is_lead_or_creator(circle, user_id):
            return CustomResponse(
                general_message="Only the circle lead or creator can view join requests"
            ).get_failure_response()

        pending = UserCircleLink.objects.filter(
            circle=circle, is_invited=False, accepted__isnull=True
        ).select_related('user')

        from .learningcircle_serializer import CircleJoinRequestSerializer
        serializer = CircleJoinRequestSerializer(pending, many=True)
        return CustomResponse(
            general_message="Pending join requests fetched successfully",
            response=serializer.data,
        ).get_success_response()

    def patch(self, request, circle_id: str):
        """Lead/creator accepts or rejects a pending join request. Body: {link_id, action: accept|reject}"""
        user_id = JWTUtils.fetch_user_id(request)

        try:
            circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(general_message="Learning Circle not found").get_failure_response()

        if not _is_lead_or_creator(circle, user_id):
            return CustomResponse(
                general_message="Only the circle lead or creator can manage join requests"
            ).get_failure_response()

        link_id = request.data.get("link_id")
        if not link_id:
            return CustomResponse(general_message="link_id is required").get_failure_response()

        try:
            link = UserCircleLink.objects.get(
                id=link_id, circle=circle, is_invited=False, accepted__isnull=True
            )
        except UserCircleLink.DoesNotExist:
            return CustomResponse(
                general_message="Pending join request not found"
            ).get_failure_response()

        action = request.data.get("action")
        if action not in ("accept", "reject"):
            return CustomResponse(
                general_message="Invalid action. Must be 'accept' or 'reject'"
            ).get_failure_response()

        if action == "accept":
            link.accepted = True
            link.accepted_at = DateTimeUtils.get_current_utc_time()
            link.save()
            return CustomResponse(
                general_message="Join request accepted. User is now a member."
            ).get_success_response()

        link.accepted = False
        link.save()
        return CustomResponse(
            general_message="Join request rejected."
        ).get_success_response()


class CircleMemberAddAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)

        try:
            circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(general_message="Learning Circle not found").get_failure_response()

        if not _is_lead_or_creator(circle, user_id):
            return CustomResponse(
                general_message="Only the circle lead or creator can add members"
            ).get_failure_response()

        target_muid = request.data.get("muid")
        if not target_muid:
            return CustomResponse(general_message="muid is required").get_failure_response()

        try:
            target_user = User.objects.get(muid=target_muid)
        except User.DoesNotExist:
            return CustomResponse(general_message="No user found with this muid").get_failure_response()

        target_user_id = target_user.id

        already_member = UserCircleLink.objects.filter(
            circle=circle, user_id=target_user_id, accepted=True
        ).exists()
        if already_member:
            return CustomResponse(
                general_message="User is already a member of this circle"
            ).get_failure_response()

        # Remove any pending invite if exists to avoid duplicate
        UserCircleLink.objects.filter(
            circle=circle, user_id=target_user_id, accepted__isnull=True
        ).delete()

        UserCircleLink.objects.create(
            id=str(uuid.uuid4()),
            user_id=target_user_id,
            circle=circle,
            lead=False,
            is_invited=False,
            accepted=True,
            accepted_at=DateTimeUtils.get_current_utc_time(),
        )
        return CustomResponse(general_message="Member added successfully").get_success_response()


class CircleInviteAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)

        try:
            circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(general_message="Learning Circle not found").get_failure_response()

        if not _is_lead_or_creator(circle, user_id):
            return CustomResponse(
                general_message="Only the circle lead or creator can send invitations"
            ).get_failure_response()

        from .learningcircle_serializer import CircleInviteSerializer
        serializer = CircleInviteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Invalid data", response=serializer.errors
            ).get_failure_response()

        target_user_id = serializer.validated_data['user_id']
        invite_as_lead = serializer.validated_data.get('lead', False)

        # Check already a member
        already_member = UserCircleLink.objects.filter(
            circle=circle, user_id=target_user_id, accepted=True
        ).exists()
        if already_member:
            return CustomResponse(
                general_message="User is already a member of this circle"
            ).get_failure_response()

        # Check pending invite already exists
        pending_invite = UserCircleLink.objects.filter(
            circle=circle, user_id=target_user_id, is_invited=True, accepted__isnull=True
        ).exists()
        if pending_invite:
            return CustomResponse(
                general_message="An invitation is already pending for this user"
            ).get_failure_response()

        UserCircleLink.objects.create(
            id=str(uuid.uuid4()),
            user_id=target_user_id,
            circle=circle,
            lead=invite_as_lead,
            is_invited=True,
            invited_by_id=user_id,
            accepted=None,
        )
        return CustomResponse(general_message="Invitation sent successfully").get_success_response()


class CircleInviteStatusAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request):
        """List all pending invitations for the current user."""
        user_id = JWTUtils.fetch_user_id(request)
        pending = UserCircleLink.objects.filter(
            user_id=user_id, is_invited=True, accepted__isnull=True
        ).select_related('circle__ig', 'invited_by')
        from .learningcircle_serializer import CircleInviteStatusSerializer
        serializer = CircleInviteStatusSerializer(pending, many=True)
        return CustomResponse(
            general_message="Invitations fetched successfully",
            response=serializer.data,
        ).get_success_response()

    def post(self, request, link_id: str):
        """Accept or reject an invitation by its link_id."""
        user_id = JWTUtils.fetch_user_id(request)

        try:
            link = UserCircleLink.objects.get(id=link_id, user_id=user_id, is_invited=True)
        except UserCircleLink.DoesNotExist:
            return CustomResponse(
                general_message="Invitation not found"
            ).get_failure_response()

        if link.accepted is not None:
            return CustomResponse(
                general_message="This invitation has already been responded to"
            ).get_failure_response()

        action = request.data.get("action")
        if action not in ("accept", "reject"):
            return CustomResponse(
                general_message="Invalid action. Must be 'accept' or 'reject'"
            ).get_failure_response()

        if action == "accept":
            link.accepted = True
            link.accepted_at = DateTimeUtils.get_current_utc_time()
            link.save()
            return CustomResponse(
                general_message="Invitation accepted successfully"
            ).get_success_response()

        link.accepted = False
        link.save()
        return CustomResponse(
            general_message="Invitation rejected successfully"
        ).get_success_response()


class CircleSentInvitesAPI(APIView):
    permission_classes = [CustomizePermission]

    def get(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)

        try:
            circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(general_message="Learning Circle not found").get_failure_response()

        if not _is_lead_or_creator(circle, user_id):
            return CustomResponse(
                general_message="Only the circle lead or creator can view sent invitations"
            ).get_failure_response()

        # Optional status filter: pending | accepted | rejected
        status_filter = request.query_params.get("status", None)
        qs = UserCircleLink.objects.filter(circle=circle, is_invited=True).select_related('user')

        if status_filter == "pending":
            qs = qs.filter(accepted__isnull=True)
        elif status_filter == "accepted":
            qs = qs.filter(accepted=True)
        elif status_filter == "rejected":
            qs = qs.filter(accepted=False)

        from .learningcircle_serializer import CircleSentInvitesSerializer
        serializer = CircleSentInvitesSerializer(qs, many=True)
        return CustomResponse(
            general_message="Sent invitations fetched successfully",
            response=serializer.data,
        ).get_success_response()


class CircleTransferLeadAPI(APIView):
    permission_classes = [CustomizePermission]

    def post(self, request, circle_id: str):
        user_id = JWTUtils.fetch_user_id(request)

        try:
            circle = LearningCircle.objects.get(id=circle_id)
        except LearningCircle.DoesNotExist:
            return CustomResponse(general_message="Learning Circle not found").get_failure_response()

        if not _is_lead_or_creator(circle, user_id):
            return CustomResponse(
                general_message="Only the circle lead or creator can transfer leadership"
            ).get_failure_response()

        # caller_link may be None if the caller is the circle creator without a UserCircleLink row
        caller_link = UserCircleLink.objects.filter(
            circle=circle, user_id=user_id, accepted=True, lead=True
        ).first()

        target_muid = request.data.get("muid")
        if not target_muid:
            return CustomResponse(general_message="muid is required").get_failure_response()

        try:
            target_user = User.objects.get(muid=target_muid)
        except User.DoesNotExist:
            return CustomResponse(general_message="No user found with this muid").get_failure_response()

        target_user_id = target_user.id

        if target_user_id == user_id:
            return CustomResponse(
                general_message="You are already the lead"
            ).get_failure_response()

        try:
            target_link = UserCircleLink.objects.get(
                circle=circle, user_id=target_user_id, accepted=True
            )
        except UserCircleLink.DoesNotExist:
            return CustomResponse(
                general_message="Target user is not an accepted member of this circle"
            ).get_failure_response()

        if target_link.lead:
            return CustomResponse(
                general_message="Target user is already the lead"
            ).get_failure_response()

        # Demote the caller only if they have an explicit lead link (creator may not)
        if caller_link:
            caller_link.lead = False
            caller_link.save()

        target_link.lead = True
        target_link.save()

        return CustomResponse(
            general_message="Lead transferred successfully"
        ).get_success_response()
