import uuid
from datetime import datetime, timedelta, timezone

import pytz


def _aware_meet_time(meet_time):
    if meet_time is None:
        return None
    if meet_time.tzinfo is None:
        return meet_time.replace(tzinfo=timezone.utc)
    return meet_time


def meeting_is_started(meet_time):
    aware_time = _aware_meet_time(meet_time)
    if aware_time is None:
        return False
    return aware_time <= DateTimeUtils.get_current_utc_time()


def meeting_is_ended(meet_time, duration_hours):
    aware_time = _aware_meet_time(meet_time)
    if aware_time is None:
        return False
    return (
        aware_time + timedelta(hours=duration_hours or 0)
    ) <= DateTimeUtils.get_current_utc_time()
from db.learning_circle import LearningCircle, CircleMeetingLog, CircleMeetingAttendees, UserCircleLink
from rest_framework import serializers

from db.organization import Organization
from db.user import User
from utils.types import LearningCircleRecurrenceType
from utils.utils import DateTimeUtils

from db.task import (
    InterestGroup,
    KarmaActivityLog,
    # Level,
    # TaskList,
    # Wallet,
    # UserIgLink,
    # UserLvlLink,
)

import collections
from django.db.models import Sum


class LearningCircleCreateEditSerialzier(serializers.ModelSerializer):
    ig = serializers.PrimaryKeyRelatedField(
        queryset=InterestGroup.objects.all(), required=True
    )
    org = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), required=True
    )
    description = serializers.CharField(required=True)

    def update(self, instance, validated_data):
        if 'ig' in validated_data:
            instance.ig = validated_data['ig']
        if 'org' in validated_data:
            instance.org = validated_data['org']
        if 'title' in validated_data:
            instance.title = validated_data['title']
        if 'description' in validated_data:
            instance.description = validated_data['description']
        
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        circle = LearningCircle.objects.create(**validated_data)
        # The creator is implicitly the lead and an accepted member. Create their
        # UserCircleLink up-front so they are counted in member totals, the circle
        # surfaces in their "My Circles" list, and membership checks stay
        # consistent. Idempotent via get_or_create.
        UserCircleLink.objects.get_or_create(
            circle=circle,
            user_id=user_id,
            defaults={
                "id": str(uuid.uuid4()),
                "lead": True,
                "is_invited": False,
                "accepted": True,
                "accepted_at": DateTimeUtils.get_current_utc_time(),
            },
        )
        return circle

    def validate(self, attrs):
        return super().validate(attrs)

    class Meta:
        model = LearningCircle
        fields = [
            "ig",
            "org",
            "title",
            "description",
        ]


class LearningCircleDetailSerializer(serializers.ModelSerializer):
    ig = serializers.CharField(source="ig.name", read_only=True)
    org = serializers.CharField(source="org.title", read_only=True, allow_null=True)
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = [
            "id",
            "ig",
            "title",
            "description",
            "org",
            "created_by",
        ]

    def to_representation(self, instance):
        # Override to add calculated fields that don't exist on the model
        data = super().to_representation(instance)
        data['rank'] = self.get_rank(instance)
        data['total_karma'] = self.get_total_karma(instance)
        data['total_members'] = self.get_total_members(instance)
        data['next_meetup'] = self.get_next_meetup(instance)
        return data

    def get_created_by(self, obj):
        # Using select_related on the initial queryset (if fetching multiple LearningCircles)
        # would make this access more efficient by avoiding a separate query for each obj.created_by.
        return {
            "id": obj.created_by.id,
            "full_name": obj.created_by.full_name,
            "profile_pic": obj.created_by.profile_pic,
            "muid": obj.created_by.muid,
        }

    def get_total_members(self, obj):
        """Calculate total number of accepted members in this circle"""
        return UserCircleLink.objects.filter(
            circle=obj.id,
            accepted=True,
        ).count()

    @property
    def _all_circle_rankings_data(self):
        """
        Calculates and caches the rankings for all circles.
        This method will only run once per serializer instance.
        """
        if not hasattr(self, '_cached_circle_rankings'):
            user_circle_links = UserCircleLink.objects.filter(accepted=True).values('circle_id', 'user_id')

            circle_to_users = collections.defaultdict(list)
            for link in user_circle_links:
                circle_to_users[link['circle_id']].append(link['user_id'])

            circle_igs = dict(LearningCircle.objects.values_list('id', 'ig_id'))

            user_karma = (
                KarmaActivityLog.objects
                .values('user_id', 'task__ig')
                .annotate(total_karma=Sum('karma'))
            )

            user_ig_karma = collections.defaultdict(int)
            for entry in user_karma:
                user_ig_karma[(entry['user_id'], entry['task__ig'])] += entry['total_karma']

            circle_data = []
            for circle_id, user_ids in circle_to_users.items():
                ig_id = circle_igs.get(circle_id)
                total = sum(user_ig_karma.get((uid, ig_id), 0) for uid in user_ids)
                circle_data.append({
                    'id': circle_id,
                    'total_karma': total
                })

            all_circle_ids = set(circle_igs.keys())
            existing_ids = {c['id'] for c in circle_data}
            for missing_id in all_circle_ids - existing_ids:
                circle_data.append({
                    'id': missing_id,
                    'total_karma': 0
                })

            circle_data.sort(key=lambda x: x['total_karma'], reverse=True)

            # Assign ranks efficiently, handling ties if necessary (though current logic doesn't)
            for i, c in enumerate(circle_data):
                c['rank'] = i + 1

            # Store as a dictionary for quick lookup by circle ID
            self._cached_circle_rankings = {item['id']: item for item in circle_data}
        return self._cached_circle_rankings

    def get_total_karma(self, obj):
        # Get total karma of learning circle
        karma_data = self._all_circle_rankings_data.get(obj.id)
        return karma_data['total_karma'] if karma_data else 0

    def get_rank(self, obj):
        # Get the rank of the current circle from pre-calculated rankings
        karma_data = self._all_circle_rankings_data.get(obj.id)
        return karma_data['rank'] if karma_data else None
    
    def _get_next_weekday(self, target_day: int):
        """Return the date of the next occurrence of target_day (1=Mon…7=Sun).
        Always returns a future date — if today is the target day, returns next week."""
        today = datetime.now()
        days_until_next = (target_day - today.isoweekday() - 1) % 7 + 1
        return (today + timedelta(days=days_until_next)).date()

    def _get_month_day(self, target_day: int):
        """Return the date of the next occurrence of target_day (1-28) in the month.
        If today is on or past that day, returns the same day next month."""
        today = datetime.now()
        month = today.month
        year = today.year
        if today.day >= target_day:
            month += 1
            if month > 12:
                month = 1
                year += 1
        return datetime(year, month, target_day).date()

    def get_next_meetup(self, obj):
        # If there's already a pending (not yet reported) meeting, return it.
        pending = (
            CircleMeetingLog.objects.filter(circle_id=obj.id, is_report_submitted=False)
            .order_by("-meet_time")
            .first()
        )
        if pending:
            return {
                **CircleMeetingLogListSerializer(pending).data,
                "is_scheduled": True,
            }

        # No pending meeting — check if the last meeting was recurring and
        # suggest the next occurrence date so the lead can one-click schedule.
        last = (
            CircleMeetingLog.objects.filter(circle_id=obj.id)
            .order_by("-meet_time")
            .first()
        )
        if not last or not last.is_recurring:
            return None

        if last.recurrence_type == LearningCircleRecurrenceType.WEEKLY.value:
            return {
                "is_scheduled": False,
                "meet_time": self._get_next_weekday(last.recurrence),
            }
        if last.recurrence_type == LearningCircleRecurrenceType.MONTHLY.value:
            return {
                "is_scheduled": False,
                "meet_time": self._get_month_day(last.recurrence),
            }
        return {"is_scheduled": False, "meet_time": None}


class LearningCircleListMinSerializer(serializers.ModelSerializer):
    ig = serializers.CharField(source="ig.name", read_only=True)
    org = serializers.CharField(source="org.title", read_only=True, allow_null=True)
    total_members = serializers.IntegerField(read_only=True)
    is_joined = serializers.SerializerMethodField()
    is_creator = serializers.SerializerMethodField()
    # attendees = serializers.SerializerMethodField()
    class Meta:
        model = LearningCircle
        # The 'attendees' field is removed as 'total_members' is used instead.
        fields = ["id", "ig", "title", "org", "total_members", "is_joined", "is_creator"]
    def to_representation(self, instance):
        # Override to add calculated fields that don't exist on the model
        data = super().to_representation(instance)
        data['total_members'] = self.get_total_members(instance)

        return data

    def get_total_members(self, obj):
        """Calculate total number of accepted members in this circle"""
        return UserCircleLink.objects.filter(
            circle=obj.id,
            accepted=True,
        ).count()

    def get_is_joined(self, obj):
        user_id = self.context.get("user_id")
        if not user_id:
            return False
        return UserCircleLink.objects.filter(
            circle=obj.id,
            user_id=user_id,
            accepted=True,
        ).exists()

    def get_is_creator(self, obj):
        user_id = self.context.get("user_id")
        if not user_id:
            return False
        return obj.created_by_id == user_id

    # def get_attendees(self, obj):
        # query = (
        #     obj.circle_meeting_log_circle_id.prefetch_related(
        #         "circle_meeting_attendance_meet_id"
        #     )
        #     .all()
        #     .only("circle_meeting_attendance_meet_id__user_id")
        # )
        # data = []
        # user_id = self.context.get("user_id")
        # cur_user_org = None
        # if user_id:
        #     try:
        #         cur_user = (
        #             User.objects.prefetch_related("user_organization_link_user")
        #             .only("user_organization_link_user__org_id")
        #             .get(id=user_id)
        #         )
        #         cur_user_org = cur_user.user_organization_link_user__org_id
        #     except:
        #         pass
        # for attendee in query.:
        #     data.append(
        #         {
        #             "full_name": attendee.user_id.full_name,
        #             "is_same_org": cur_user_org
        #             in attendee.user_id.user_organization_link_user.all().values_list(
        #                 "org_id", flat=True
        #             ),
        #         }
        #     )
        # return data
        # return []


class CircleMeetingLogCreateEditSerializer(serializers.ModelSerializer):
    ONLINE_PLATFORM_CHOICES = ("Zoom", "Google Meet", "Microsoft Teams","Discord", "Other")

    circle_id = serializers.PrimaryKeyRelatedField(
        queryset=LearningCircle.objects.all(), required=True
    )
    # Online fields
    platform = serializers.ChoiceField(
        choices=ONLINE_PLATFORM_CHOICES, required=False, allow_null=True,
        help_text="Required for online meetings. One of: Zoom, Google Meet, Microsoft Teams, Other"
    )
    meet_link = serializers.URLField(
        required=False, allow_null=True,
        help_text="Required for online meetings. Full URL of the meeting."
    )
    # Offline fields
    meet_place = serializers.CharField(
        required=False, allow_null=True,
        help_text="Required for offline meetings. Address/venue name."
    )
    coord_x = serializers.FloatField(
        required=False, allow_null=True,
        help_text="Required for offline meetings. Latitude coordinate."
    )
    coord_y = serializers.FloatField(
        required=False, allow_null=True,
        help_text="Required for offline meetings. Longitude coordinate."
    )

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        instance.is_recurring = validated_data.get("is_recurring", instance.is_recurring)
        instance.recurrence_type = validated_data.get("recurrence_type", instance.recurrence_type)
        instance.recurrence = validated_data.get("recurrence", instance.recurrence)
        instance.is_report_needed = validated_data.get(
            "is_report_needed", instance.is_report_needed
        )
        instance.report_description = validated_data.get(
            "report_description", instance.report_description
        )
        instance.mode = validated_data.get("mode", instance.mode)
        instance.coord_x = validated_data.get("coord_x", instance.coord_x)
        instance.coord_y = validated_data.get("coord_y", instance.coord_y)
        instance.meet_place = validated_data.get("meet_place", instance.meet_place)
        instance.meet_link = validated_data.get("meet_link", instance.meet_link)
        instance.meet_time = validated_data.get("meet_time", instance.meet_time)
        instance.duration = validated_data.get("duration", instance.duration)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        meet_code = self.context.get("meet_code")
        validated_data["created_by_id"] = user_id
        validated_data["meet_code"] = meet_code
        validated_data.pop("platform", None)  # platform is not a DB field; used only in validate()
        meet = CircleMeetingLog.objects.create(**validated_data)
        CircleMeetingAttendees.objects.create(
            meet_id=meet, user_id_id=user_id, is_joined=True, joined_at=datetime.now()
        )
        return meet

    def validate_meet_time(self, value):
        if value:
            aware_time = _aware_meet_time(value)
            if aware_time <= DateTimeUtils.get_current_utc_time():
                raise serializers.ValidationError("Meeting time must be in the future.")
        return value

    def validate(self, attrs):
        is_report_needed = attrs.get("is_report_needed")
        report_description = attrs.get("report_description")
        mode = attrs.get("mode")

        # --- Report validation ---
        if not is_report_needed:
            attrs["report_description"] = None
        else:
            if not report_description:
                raise serializers.ValidationError("Report description is required when report is needed.")

        # --- Mode-specific validation ---
        if mode == "online":
            # Online: require platform + meet_link; clear offline-only fields
            if not attrs.get("platform"):
                raise serializers.ValidationError(
                    "platform is required for online meetings. "
                    "Choices: {}".format(", ".join(self.ONLINE_PLATFORM_CHOICES))
                )
            if not attrs.get("meet_link"):
                raise serializers.ValidationError(
                    "meet_link (meeting URL) is required for online meetings."
                )
            # Clear offline fields — online meetings have no physical location
            attrs["coord_x"] = 0.0
            attrs["coord_y"] = 0.0
            attrs["meet_place"] = attrs.get("platform")  # store platform name in meet_place

        elif mode == "offline":
            # Offline: require address, coordinates; clear online-only fields
            if not attrs.get("meet_place"):
                raise serializers.ValidationError(
                    "meet_place (venue address) is required for offline meetings."
                )
            coord_x = attrs.get("coord_x")
            coord_y = attrs.get("coord_y")
            if coord_x is None or coord_y is None:
                raise serializers.ValidationError(
                    "coord_x (latitude) and coord_y (longitude) are required for offline meetings."
                )
            # Clear online fields
            attrs["meet_link"] = None
            attrs["platform"] = None
        else:
            raise serializers.ValidationError(
                "mode must be either \"online\" or \"offline\"."
            )

        # --- Recurrence validation ---
        is_recurring = attrs.get("is_recurring")
        recurrence_type = attrs.get("recurrence_type")
        recurrence = attrs.get("recurrence")
        if not is_recurring:
            attrs["recurrence_type"] = None
            attrs["recurrence"] = None
        else:
            if not recurrence_type or not recurrence:
                raise serializers.ValidationError(
                    "recurrence_type and recurrence are required for recurring meetings."
                )
            if recurrence_type not in LearningCircleRecurrenceType.get_all_values():
                raise serializers.ValidationError(
                    "Invalid recurrence_type. Valid values: {}".format(
                        LearningCircleRecurrenceType.get_all_values()
                    )
                )
            if recurrence_type == LearningCircleRecurrenceType.WEEKLY.value:
                if recurrence < 1 or recurrence > 7:
                    raise serializers.ValidationError(
                        "recurrence must be between 1-7 for weekly meetings (day of week)."
                    )
            elif recurrence_type == LearningCircleRecurrenceType.MONTHLY.value:
                if recurrence < 1 or recurrence > 28:
                    raise serializers.ValidationError(
                        "recurrence must be between 1-28 for monthly meetings (day of month)."
                    )

        return super().validate(attrs)

    # def validate_circle_id(self, value):
    #     if CircleMeetingLog.objects.filter(
    #         circle_id=value, is_report_submitted=False
    #     ).exists():
    #         raise serializers.ValidationError(
    #             "There is already an ongoing meeting for this learning circle"
    #         )
    #     return value

    class Meta:
        model = CircleMeetingLog
        fields = [
            "circle_id",
            "title",
            "description",
            "mode",
            # Online fields
            "platform",
            "meet_link",
            # Offline fields
            "meet_place",
            "coord_x",
            "coord_y",
            # Scheduling
            "meet_time",
            "duration",
            # Recurrence
            "is_recurring",
            "recurrence_type",
            "recurrence",
            # Report
            "is_report_needed",
            "report_description",
        ]


class CircleMeetingLogListSerializer(serializers.ModelSerializer):
    circle = serializers.CharField(source="circle_id.id", read_only=True)
    created_by = serializers.CharField(source="created_by_id.full_name", read_only=True)
    is_started = serializers.SerializerMethodField()
    is_ended = serializers.SerializerMethodField()

    def get_is_started(self, obj):
        return meeting_is_started(obj.meet_time)

    def get_is_ended(self, obj):
        return meeting_is_ended(obj.meet_time, obj.duration)

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "circle",
            "meet_code",
            "title",
            "description",
            "mode",
            "is_recurring",
            "recurrence_type",
            "recurrence",
            "is_report_needed",
            "report_description",
            "coord_x",
            "coord_y",
            "meet_place",
            "meet_link",
            "meet_time",
            "duration",
            "created_by",
            "is_started",
            "is_ended",
            "is_report_submitted",
        ]


class CircleMeetingAttendeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = CircleMeetingAttendees
        fields = ["is_joined", "is_report_submitted", "is_lc_approved"]


class CircleMeetupInfoSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    is_report_needed = serializers.BooleanField(read_only=True)
    report_description = serializers.CharField(read_only=True)
    coord_x = serializers.FloatField(read_only=True)
    coord_y = serializers.FloatField(read_only=True)
    meet_place = serializers.CharField(read_only=True)
    meet_time = serializers.DateTimeField(read_only=True)
    duration = serializers.IntegerField(read_only=True)
    # is_approved = serializers.BooleanField(read_only=True)
    is_started = serializers.SerializerMethodField()
    is_ended = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    attendees = serializers.SerializerMethodField()
    meet_code = serializers.SerializerMethodField()
    ig = serializers.CharField(source="circle_id.ig.name", read_only=True)
    created_by_id = serializers.CharField(source="created_by.id", read_only=True)

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "title",
            "description",
            "mode",
            "meet_place",
            "meet_link",
            "meet_time",
            "ig",
            "is_report_needed",
            "report_description",
            "coord_x",
            "coord_y",
            "duration",
            "is_started",
            "is_ended",
            "attendees",
            "is_member",
            "meet_code",
            "created_by_id",
        ]

    def get_is_member(self, obj):
        user_id = self.context.get("user_id")
        if not user_id:
            return False
        if obj.created_by_id == user_id:
            return True
        return UserCircleLink.objects.filter(
            circle_id=obj.circle_id_id,
            user_id=user_id,
            accepted=True,
        ).exists()

    def get_meet_code(self, obj):
        user_id = self.context.get("user_id")
        if not obj.created_by_id == user_id:
            return None
        return obj.meet_code

    def get_is_started(self, obj):
        return meeting_is_started(obj.meet_time)

    def get_is_ended(self, obj):
        return meeting_is_ended(obj.meet_time, obj.duration)

    def get_attendees(self, obj):
        query = (
            obj.circle_meeting_attendance_meet_id.select_related("user_id")
            .prefetch_related("user_id__user_organization_link_user")
            .only(
                "user_id__full_name",
                "is_joined",
                "is_report_submitted",
                "user_id__user_organization_link_user__org_id",
            )
            .all()
        )
        data = []
        user_id = self.context.get("user_id")
        cur_user_org = None
        cur_user_orgs = set()
        if user_id:
            try:
                from db.organization import UserOrganizationLink

                cur_user_orgs = set(
                    UserOrganizationLink.objects.filter(user_id=user_id).values_list(
                        "org_id", flat=True
                    )
                )
            except Exception:
                pass
        for attendee in query:
            attendee_orgs = set(
                attendee.user_id.user_organization_link_user.all().values_list(
                    "org_id", flat=True
                )
            )
            data.append(
                {
                    "user_id": attendee.user_id.id,
                    "full_name": attendee.user_id.full_name,
                    "is_joined": attendee.is_joined,
                    "is_creator": attendee.user_id.id == obj.created_by_id,
                    "is_report_submitted": attendee.is_report_submitted,
                    "profile_pic": attendee.user_id.profile_pic,
                    "is_same_org": bool(cur_user_orgs & attendee_orgs),
                }
            )
        return data


class CircleMeetupPublicSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    org = serializers.CharField(source="circle_id.org.title", read_only=True)
    meet_place = serializers.CharField(read_only=True)
    meet_time = serializers.DateTimeField(read_only=True)
    is_started = serializers.SerializerMethodField()
    is_ended = serializers.SerializerMethodField()
    ig_id = serializers.CharField(source="circle_id.ig.id", read_only=True)
    ig_name = serializers.CharField(source="circle_id.ig.name", read_only=True)
    created_by = serializers.CharField(source="created_by.full_name", read_only=True)

    def get_is_started(self, obj):
        return meeting_is_started(obj.meet_time)

    def get_is_ended(self, obj):
        return meeting_is_ended(obj.meet_time, obj.duration)

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "title",
            "description",
            "org",
            "ig_id",
            "ig_name",
            "mode",
            "is_recurring",
            "recurrence_type",
            "recurrence",
            "meet_place",
            "circle_id",
            "meet_time",
            "meet_link",
            "is_started",
            "is_ended",
            "created_by",
        ]


class CircleMeetupMinSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    coord_x = serializers.FloatField(read_only=True)
    org = serializers.CharField(source="circle_id.org.title", read_only=True)
    coord_y = serializers.FloatField(read_only=True)
    meet_place = serializers.CharField(read_only=True)
    meet_time = serializers.DateTimeField(read_only=True)
    # meet_code = serializers.CharField(read_only=True)
    circle_id = serializers.CharField(read_only=True, source="circle_id.id")
    is_started = serializers.SerializerMethodField()
    is_ended = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    is_rsvp = serializers.SerializerMethodField()
    attendees_count = serializers.SerializerMethodField()
    created_by = serializers.CharField(source="created_by.full_name", read_only=True)
    created_by_id = serializers.CharField(source="created_by.id", read_only=True)
    ig_id = serializers.CharField(source="circle_id.ig.id", read_only=True)
    ig_name = serializers.CharField(source="circle_id.ig.name", read_only=True)

    def get_is_started(self, obj):
        return meeting_is_started(obj.meet_time)

    def get_is_ended(self, obj):
        return meeting_is_ended(obj.meet_time, obj.duration)

    def get_is_joined(self, obj):
        if user_id := self.context.get("user_id"):
            attendee = obj.circle_meeting_attendance_meet_id.filter(
                user_id=user_id
            ).first()
            if attendee:
                return attendee.is_joined
        return False

    def get_is_rsvp(self, obj):
        if user_id := self.context.get("user_id"):
            return obj.circle_meeting_attendance_meet_id.filter(
                user_id=user_id
            ).exists()
        return False

    def get_attendees_count(self, obj):
        return obj.circle_meeting_attendance_meet_id.count()

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "title",
            "description",
            "org",
            "ig_id",
            "ig_name",
            "mode",
            "is_recurring",
            "recurrence_type",
            "recurrence",
            "meet_place",
            "is_rsvp",
            # "meet_code",
            "circle_id",
            "coord_x",
            "coord_y",
            "meet_time",
            "meet_link",
            "is_started",
            "is_ended",
            "is_joined",
            "attendees_count",
            "created_by",
            "created_by_id",
        ]


# # class LearningCircleKarmaSerializer(serializers.ModelSerializer):
#     total_karma = serializers.SerializerMethodField()
#     rank = serializers.SerializerMethodField()
#     member_count = serializers.SerializerMethodField()
    
#     class Meta:
#         model = LearningCircle
#         fields = ['id', 'title', 'ig', 'total_karma', 'rank', 'member_count']
    
#     def get_total_karma(self, obj):
#         # Get all members (attendees) of this circle's meetings
#         members = CircleMeetingAttendees.objects.filter(
#             meet_id__circle_id=obj,
#             is_joined=True
#         ).values_list('user_id', flat=True).distinct()
        
#         # Sum karma points for these members related to this circle's interest group
#         total_karma = 0
#         for member_id in members:
#             # Filter KarmaActivityLog for the member and tasks related to the specific IG
#             user_karma = KarmaActivityLog.objects.filter(
#             user_id=member_id,  # Filter by user
#             task__ig=obj.ig,    # Filter by the IG related to the task
#             ).aggregate(total=models.Sum('karma'))['total'] or 0
#             total_karma += user_karma
            
#         return total_karma
        
#     def get_rank(self, obj):
#         # Get all circles and sort by karma
#         all_circles = LearningCircle.objects.all()
#         ranked_circles = sorted(
#             all_circles, 
#             key=lambda circle: self.get_total_karma(circle),
#             reverse=True
#         )
        
#         # Find position of current circle
#         for index, circle in enumerate(ranked_circles):
#             if circle.id == obj.id:
#                 return index + 1  # 1-based ranking
#         return None
    
#     def get_member_count(self, obj):
#         return CircleMeetingAttendees.objects.filter(
#             meet_id__circle_id=obj,
#             is_joined=True
#         ).values('user_id').distinct().count()

# --- New Serializers ---


class UserCircleListSerializer(serializers.ModelSerializer):
    """Serializes a UserCircleLink entry for the 'My Circles' list."""
    circle_id = serializers.CharField(source='circle.id', read_only=True)
    title = serializers.CharField(source='circle.title', read_only=True)
    ig = serializers.CharField(source='circle.ig.name', read_only=True)
    org = serializers.CharField(source='circle.org.title', read_only=True, allow_null=True)
    is_lead = serializers.BooleanField(source='lead', read_only=True)
    total_members = serializers.SerializerMethodField()
    joined_at = serializers.DateTimeField(source='accepted_at', read_only=True)

    def get_total_members(self, obj):
        return UserCircleLink.objects.filter(circle=obj.circle_id, accepted=True).count()

    class Meta:
        model = UserCircleLink
        fields = ['circle_id', 'title', 'ig', 'org', 'is_lead', 'total_members', 'joined_at']


class CircleInviteSerializer(serializers.Serializer):
    """Validates the invite request body for POST /invite/<circle_id>/."""
    muid = serializers.CharField(required=True, help_text="muid of the user to invite, e.g. user@mulearn")
    lead = serializers.BooleanField(required=False, default=False)

    def validate_muid(self, value):
        user = User.objects.filter(muid=value).first()
        if not user:
            raise serializers.ValidationError("No user found with this muid.")
        return user.id  # Store resolved user_id under the 'muid' key

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        # Rename resolved muid -> user_id for use in the view
        ret['user_id'] = ret.pop('muid')
        return ret


class CircleInviteStatusSerializer(serializers.ModelSerializer):
    """Serializes a pending invitation from the invitee's perspective."""
    link_id = serializers.CharField(source='id', read_only=True)
    circle_id = serializers.CharField(source='circle.id', read_only=True)
    circle_title = serializers.CharField(source='circle.title', read_only=True)
    ig = serializers.CharField(source='circle.ig.name', read_only=True)
    is_lead_invite = serializers.BooleanField(source='lead', read_only=True)
    invited_by = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(read_only=True)

    def get_invited_by(self, obj):
        if obj.invited_by:
            return {
                'user_id': obj.invited_by.id,
                'full_name': obj.invited_by.full_name,
                'profile_pic': obj.invited_by.profile_pic,
            }
        return None

    class Meta:
        model = UserCircleLink
        fields = ['link_id', 'circle_id', 'circle_title', 'ig',
                  'is_lead_invite', 'invited_by', 'created_at']


class CircleSentInvitesSerializer(serializers.ModelSerializer):
    """Serializes outgoing invites from the lead's perspective."""
    link_id = serializers.CharField(source='id', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    profile_pic = serializers.CharField(source='user.profile_pic', read_only=True, allow_null=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    is_lead_invite = serializers.BooleanField(source='lead', read_only=True)
    status = serializers.SerializerMethodField()
    invited_at = serializers.DateTimeField(source='created_at', read_only=True)

    def get_status(self, obj):
        if obj.accepted is None:
            return 'pending'
        return 'accepted' if obj.accepted else 'rejected'

    class Meta:
        model = UserCircleLink
        fields = ['link_id', 'user_id', 'full_name', 'profile_pic', 'muid',
                  'is_lead_invite', 'status', 'invited_at']


class CircleJoinRequestSerializer(serializers.ModelSerializer):
    """Serializes a user-initiated join request (is_invited=False, accepted=None) from the lead's perspective."""
    link_id = serializers.CharField(source='id', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    profile_pic = serializers.CharField(source='user.profile_pic', read_only=True, allow_null=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    requested_at = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = UserCircleLink
        fields = ['link_id', 'user_id', 'full_name', 'profile_pic', 'muid', 'requested_at']
