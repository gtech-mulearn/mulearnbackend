from datetime import datetime, timedelta, timezone
import requests
from rest_framework.views import APIView
from db.learning_circle import LearningCircle, CircleMeetingLog, CircleMeetingAttendees, UserCircleLink
from utils.utils import CommonUtils

# from db.user import UserInterests
from db.user import UserDomains
from utils.karma import add_karma
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import Lc
from utils.utils import DateTimeUtils, generate_code
from .learningcircle_serializer import (
    CircleMeetingLogCreateEditSerializer,
    CircleMeetupInfoSerializer,
    CircleMeetupMinSerializer,
    CircleMeeupPublicSerializer,
    LearningCircleCreateEditSerialzier,
    LearningCircleDetailSerializer,
    LearningCircleListMinSerializer,
)
from django.db.models import Sum, F, Q
from db.user import User
from db.task import (
    KarmaActivityLog,
    
)
from collections import defaultdict

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


class LearningCircleMeetingListView(APIView):
    def get(self, request, circle_id: str):
        learning_circle = LearningCircle.objects.get(id=circle_id)
        circle_meetings = CircleMeetingLog.objects.filter(circle_id=learning_circle)
        serializer = CircleMeetupMinSerializer(circle_meetings, many=True)
        return CustomResponse(
            general_message="Circle Meetings fetched successfully",
            response=serializer.data,
        ).get_success_response()


class LearningCircleMeetingView(APIView):
    permission_classes = [CustomizePermission]

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
        is_meet_started = circle_meeting.meet_time <= (
            DateTimeUtils.get_current_utc_time() + timedelta(hours=2)
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

        serializer = CircleMeeupPublicSerializer(
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





class LearningCircleBasicDetailsView(APIView):

    def get(self, request, circle_id):
        try:
            circle = LearningCircle.objects.select_related('ig').get(id=circle_id)
            member_count = UserCircleLink.objects.filter(
                circle_id=circle.id,
                accepted=True
            ).count()
            # Calculate total karma
            member_ids = UserCircleLink.objects.filter(
                circle_id=circle_id,
                accepted=True
            ).values_list('user_id', flat=True)
            
            total_karma = KarmaActivityLog.objects.filter(
                user_id__in=member_ids,
                task__ig=circle.ig
            ).aggregate(total=Sum('karma'))['total'] or 0
            
            # Calculate circle rankings using Django ORM
            circle_karma = self.get_circle_rankings()
            
            # Find the rank of the current circle
            circle_rank = next((item['rank'] for item in circle_karma if item['id'] == circle_id), None)
            
            # Get pending invitations count
            pending_invites = UserCircleLink.objects.filter(
                circle_id=circle_id,
                is_invited=1,
                accepted__isnull=True
            ).count()
            
            response_data = {
                'circle_id': circle.id,
                'circle_title': circle.title,
                'ig_id': circle.ig_id,
                'ig_name': circle.ig.name,
                'member_count': member_count,
                'total_karma': total_karma,
                'rank': circle_rank,
                'pending_invites': pending_invites,
            }
            
            return CustomResponse(
                general_message="Learning Circle basic details fetched successfully",
                response=response_data
            ).get_success_response()
        
        except LearningCircle.DoesNotExist:
            return CustomResponse(
                general_message="Learning Circle not found"
            ).get_failure_response()
    
    @staticmethod
    def get_circle_rankings():
    
        user_circle_links = UserCircleLink.objects.filter(accepted=True).values('circle_id', 'user_id')
        
        circle_to_users = defaultdict(list)
        for link in user_circle_links:
            circle_to_users[link['circle_id']].append(link['user_id'])
        
        circle_igs = dict(LearningCircle.objects.values_list('id', 'ig_id'))
        
        user_karma = (
            KarmaActivityLog.objects
            .values('user_id', 'task__ig')
            .annotate(total_karma=Sum('karma'))
        )

        # Build a user-IG karma map
        user_ig_karma = defaultdict(int)
        for entry in user_karma:
            user_ig_karma[(entry['user_id'], entry['task__ig'])] += entry['total_karma']

        # Build circle karma list
        circle_data = []
        for circle_id, user_ids in circle_to_users.items():
            ig_id = circle_igs.get(circle_id)
            total = sum(user_ig_karma.get((uid, ig_id), 0) for uid in user_ids)
            circle_data.append({
                'id': circle_id,
                'total_karma': total
            })

        # Include circles with no members (0 karma)
        all_circle_ids = set(circle_igs.keys())
        existing_ids = {c['id'] for c in circle_data}
        for missing_id in all_circle_ids - existing_ids:
            circle_data.append({
                'id': missing_id,
                'total_karma': 0
            })

        # Sort and assign rank
        circle_data.sort(key=lambda x: x['total_karma'], reverse=True)
        for i, c in enumerate(circle_data):
            c['rank'] = i + 1

        return circle_data
    

class LearningCircleMemberDetailsView(APIView):

    def get(self, request, circle_id):
        try:
            circle = LearningCircle.objects.select_related('ig').get(id=circle_id)
            
            member_links = UserCircleLink.objects.filter(
                circle_id=circle_id,
                accepted=True
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
          
            for link in member_links:
                user_id = link.user_id
                user = users.get(user_id)
                if not user:
                    continue
                member_details = []
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
            
            return CustomResponse(
                general_message="Learning Circle member details fetched successfully",
                response=member_details
            ).get_success_response()
        
        except LearningCircle.DoesNotExist:
            return CustomResponse(
                general_message="Learning Circle not found"
            ).get_failure_response()
            
            
class LearningCircleManageRequestsView(APIView):
  
    def get(self, request, circle_id):
        try:
            circle = LearningCircle.objects.get(id=circle_id)
           
            pending_requests = UserCircleLink.objects.filter(
                circle_id=circle_id,
                accepted__isnull=True
            ).select_related('user')
            
            if not pending_requests.exists():
                return CustomResponse(
                    general_message="No pending requests to join.",
                    response=[]
                ).get_success_response()
                
            pending_requests_data = [
                {
                    "user_id": request.user_id,
                    "full_name": request.user.full_name,
                    "email": request.user.email
                }
                for request in pending_requests
            ]
            
            return CustomResponse(
                general_message="Pending requests fetched successfully.",
                response=pending_requests_data
            ).get_success_response()

        except LearningCircle.DoesNotExist:
            return CustomResponse(
                general_message="Learning Circle not found."
            ).get_failure_response()

        except Exception as e:
            return CustomResponse(
                general_message=f"An error occurred: {str(e)}"
            ).get_failure_response()

    def post(self, request, circle_id):
        try:
            user_id = request.data.get('user_id')
            action = request.data.get('action')  
            
            if action not in ["accept", "reject"]:
                return CustomResponse(
                    general_message="Invalid action. Use 'accept' or 'reject'."
                ).get_failure_response()
            
            admin_user_id = request.user.id
            is_admin = UserCircleLink.objects.filter(
                circle_id=circle_id,
                user_id=admin_user_id,
                lead=True,
                accepted=True
            ).exists()
            
            if not is_admin:
                return CustomResponse(
                    general_message="You do not have permission to manage this circle."
                ).get_failure_response()
     
            link = UserCircleLink.objects.filter(
                circle_id=circle_id,
                user_id=user_id,
                accepted__isnull=True
            ).first()
            
            if not link:
                return CustomResponse(
                    general_message="No pending request found for this user."
                ).get_failure_response()
            
            if action == "accept":
                link.accepted = True
                link.save()
                return CustomResponse(
                    general_message="User request accepted successfully."
                ).get_success_response()
            
            if action == "reject":
                link.delete()
                return CustomResponse(
                    general_message="User request rejected successfully."
                ).get_success_response()
        
        except LearningCircle.DoesNotExist:
            return CustomResponse(
                general_message="Learning Circle not found"
            ).get_failure_response()
        except Exception as e:
            return CustomResponse(
                general_message=f"An error occurred: {str(e)}"
            ).get_failure_response()
            

class LearningCircleCreateOnlineMeetingView(APIView):
    """
    API to create an online meeting for a learning circle.
    Only admins or leaders of the learning circle can create meetings.
    """
    # permission_classes = [CustomizePermission]

    def post(self, request, circle_id):
        try:
            # Fetch the authenticated user's ID with error handling
            try:
                user_id = JWTUtils.fetch_user_id(request)
                if not user_id:
                    return CustomResponse(
                        general_message="Authentication failed. User ID not found."
                    ).get_failure_response()
            except Exception as jwt_error:
                return CustomResponse(
                    general_message="Authentication failed. Invalid token."
                ).get_failure_response()

            # Validate circle_id parameter
            try:
                circle_id = int(circle_id)
            except (ValueError, TypeError):
                return CustomResponse(
                    general_message="Invalid circle ID provided."
                ).get_failure_response()

            # Fetch the learning circle with better error handling
            try:
                learning_circle = LearningCircle.objects.get(id=circle_id)
            except LearningCircle.DoesNotExist:
                return CustomResponse(
                    general_message="Learning Circle not found."
                ).get_failure_response()

            # Check if the user is an admin or leader of the circle
            try:
                is_leader = UserCircleLink.objects.filter(
                    circle_id=circle_id,
                    user_id=user_id,
                    lead=True,
                    accepted=True
                ).exists()
            except Exception as db_error:
                return CustomResponse(
                    general_message="Error checking user permissions."
                ).get_failure_response()

            if not is_leader:
                return CustomResponse(
                    general_message="You do not have permission to create a meeting in this circle."
                ).get_failure_response()

            # Extract data from the request with safe access
            title = request.data.get("title", "") if hasattr(request, 'data') and request.data else ""
            description = request.data.get("description", "") if hasattr(request, 'data') and request.data else ""
            meet_time = request.data.get("meet_time") if hasattr(request, 'data') and request.data else None
            duration = request.data.get("duration") if hasattr(request, 'data') and request.data else None
            meet_link = request.data.get("meet_link") if hasattr(request, 'data') and request.data else None

            # Validate required fields
            if not meet_link:
                return CustomResponse(
                    general_message="Meeting creation failed. 'meet_link' is required for online meetings."
                ).get_failure_response()

            # Generate a unique meeting code with error handling
            try:
                meet_code = generate_code()
                if not meet_code:
                    raise ValueError("Failed to generate meeting code")
            except Exception as code_error:
                return CustomResponse(
                    general_message="Failed to generate meeting code."
                ).get_failure_response()

            # Prepare data for serializer
            meeting_data = {
                "title": title,
                "description": description,
                "meet_time": meet_time,
                "duration": duration,
                "mode": "online",
                "meet_link": meet_link,
                "circle_id": circle_id,
                "created_by": user_id,
                "meet_code": meet_code,
            }

            # Use serializer to validate and create the meeting
            try:
                serializer = CircleMeetingLogCreateEditSerializer(data=meeting_data)
                if not serializer.is_valid():
                    return CustomResponse(
                        general_message="Meeting creation failed",
                        response=serializer.errors
                    ).get_failure_response()

                # Save the meeting
                meeting = serializer.save()
                
                return CustomResponse(
                    general_message="Meeting created successfully",
                    response={
                        "meet_code": meet_code,
                        "meeting_id": meeting.id if hasattr(meeting, 'id') else None
                    }
                ).get_success_response()
                
            except Exception as serializer_error:
                return CustomResponse(
                    general_message="Failed to create meeting due to data validation error."
                ).get_failure_response()

        except Exception as e:
            # Log the actual error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in LearningCircleCreateOnlineMeetingView: {str(e)}")
            
            return CustomResponse(
                general_message="An unexpected error occurred while creating the meeting."
            ).get_failure_response()