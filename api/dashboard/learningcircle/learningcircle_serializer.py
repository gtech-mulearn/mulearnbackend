from datetime import datetime, timedelta, timezone

import pytz
from db.learning_circle import LearningCircle, CircleMeetingLog, CircleMeetingAttendees
from rest_framework import serializers

from db.organization import Organization
from db.task import InterestGroup
from db.user import User
from utils.types import LearningCircleRecurrenceType
from utils.utils import DateTimeUtils


class LearningCircleCreateEditSerialzier(serializers.ModelSerializer):
    ig = serializers.PrimaryKeyRelatedField(
        queryset=InterestGroup.objects.all(), required=True
    )
    org = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(), required=True
    )
    description = serializers.CharField(required=True)

    def update(self, instance, validated_data):
        instance.ig_id = validated_data.get("ig_id", instance.ig_id)
        instance.org_id = validated_data.get("org_id", instance.org_id)
        instance.is_recurring = validated_data.get(
            "is_recurring", instance.is_recurring
        )
        instance.recurrence_type = validated_data.get(
            "recurrence_type", instance.recurrence_type
        )
        instance.recurrence = validated_data.get("recurrence", instance.recurrence)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        return LearningCircle.objects.create(**validated_data)

    def validate(self, attrs):
        is_recurring = attrs.get("is_recurring")
        recurrence_type = attrs.get("recurrence_type")
        recurrence = attrs.get("recurrence")
        if not is_recurring:
            attrs["recurrence_type"] = None
            attrs["recurrence"] = None
        else:
            if not recurrence_type or not recurrence:
                raise serializers.ValidationError(
                    "Recurrence type and recurrence are required for recurring learning circles"
                )
            if recurrence_type not in LearningCircleRecurrenceType.get_all_values():
                raise serializers.ValidationError("Invalid recurrence type.")
            if recurrence_type == LearningCircleRecurrenceType.WEEKLY.value:
                if recurrence < 1 or recurrence > 7:
                    raise serializers.ValidationError(
                        "Recurrence should be between 1 and 7 for weekly learning circles"
                    )
            elif recurrence_type == LearningCircleRecurrenceType.MONTHLY.value:
                if recurrence < 1 or recurrence > 28:
                    raise serializers.ValidationError(
                        "Recurrence should be between 1 and 28 for monthly learning circles"
                    )
        return super().validate(attrs)

    class Meta:
        model = LearningCircle
        fields = [
            "ig",
            "org",
            "is_recurring",
            "recurrence_type",
            "recurrence",
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
            "is_recurring",
            "recurrence_type",
            "recurrence",
            "created_by",
        ]

    def get_created_by(self, obj):
        return {
            "full_name": obj.created_by.full_name,
            "profile_pic": obj.created_by.profile_pic,
            "muid": obj.created_by.muid,
        }

    # next_meetup = serializers.SerializerMethodField()

    # def _get_next_weekday(self, target_day: int):
    #     today = datetime.now()
    #     current_day = today.isoweekday() + 2
    #     current_day = current_day if current_day <= 7 else 1
    #     days_until_next = ((target_day - current_day + 7) % 7) + 1
    #     days_until_next = days_until_next or 7
    #     next_day_date = today + timedelta(days=days_until_next)
    #     return next_day_date.date()

    # def _get_month_day(self, target_day: int):
    #     today = datetime.now()
    #     current_day = today.day
    #     current_month = today.month
    #     current_year = today.year
    #     if current_day >= target_day:
    #         current_month += 1
    #         if current_month > 12:
    #             current_month = 1
    #             current_year += 1
    #     return datetime(current_year, current_month, target_day).date()

    # def get_next_meetup(self, obj):
    #     next_meetup = (
    #         CircleMeetingLog.objects.filter(circle_id=obj.id)
    #         .filter(
    #             # meet_time__gte=DateTimeUtils.get_current_utc_time(),
    #             is_report_submitted=False,
    #         )
    #         .order_by("-meet_time")
    #         .first()
    #     )
    #     if next_meetup:
    #         return {
    #             **CircleMeetingLogListSerializer(next_meetup).data,
    #             "is_scheduled": True,
    #         }
    #     if not obj.is_recurring:
    #         return None
    #     if obj.recurrence_type == LearningCircleRecurrenceType.WEEKLY.value:
    #         return {
    #             "is_scheduled": False,
    #             "meet_time": self._get_next_weekday(obj.recurrence),
    #         }
    #     if obj.recurrence_type == LearningCircleRecurrenceType.MONTHLY.value:
    #         return {
    #             "is_scheduled": False,
    #             "meet_time": self._get_month_day(obj.recurrence),
    #         }
    #     return {"is_scheduled": False, "meet_time": None}


class LearningCircleListMinSerializer(serializers.ModelSerializer):
    ig = serializers.CharField(source="ig.name", read_only=True)
    org = serializers.CharField(source="org.title", read_only=True, allow_null=True)
    attendees = serializers.SerializerMethodField()

    def get_attendees(self, obj):
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
        return []

    class Meta:
        model = LearningCircle
        fields = ["id", "ig", "title", "org", "attendees"]


class CircleMeetingLogCreateEditSerializer(serializers.ModelSerializer):
    ONLINE_MEET_PLACE_CHOICES = ("Zoom", "Google Meet", "Microsoft Teams", "Other")
    circle_id = serializers.PrimaryKeyRelatedField(
        queryset=LearningCircle.objects.all(), required=True
    )
    meet_link = serializers.URLField(required=False, allow_null=True)
    meet_place = serializers.CharField(required=True)

    def update(self, instance, validated_data):
        instance.title = validated_data.get("title", instance.title)
        instance.is_report_needed = validated_data.get(
            "is_report_needed", instance.is_report_needed
        )
        instance.report_description = validated_data.get(
            "report_description", instance.report_description
        )
        instance.coord_x = validated_data.get("coord_x", instance.coord_x)
        instance.coord_y = validated_data.get("coord_y", instance.coord_y)
        instance.meet_place = validated_data.get("meet_place", instance.meet_place)
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
        meet = CircleMeetingLog.objects.create(**validated_data)
        CircleMeetingAttendees.objects.create(
            meet_id=meet, user_id_id=user_id, is_joined=True, joined_at=datetime.now()
        )
        return meet

    def validate(self, attrs):
        is_report_needed = attrs.get("is_report_needed")
        report_description = attrs.get("report_description")
        mode = attrs.get("mode")
        meet_place = attrs.get("meet_place")
        if not is_report_needed:
            attrs["report_description"] = None
        else:
            if not report_description:
                raise serializers.ValidationError("Report description is required")
        if mode == "online":
            if not attrs.get("meet_link"):
                raise serializers.ValidationError(
                    "Meeting link is required for online mode"
                )
            if meet_place not in self.ONLINE_MEET_PLACE_CHOICES:
                raise serializers.ValidationError(
                    "Invalid meet place, meet place should be one of {}".format(
                        self.ONLINE_MEET_PLACE_CHOICES
                    )
                )
        return super().validate(attrs)

    def validate_circle_id(self, value):
        if CircleMeetingLog.objects.filter(
            circle_id=value, is_report_submitted=False
        ).exists():
            raise serializers.ValidationError(
                "There is already an ongoing meeting for this learning circle"
            )
        return value

    class Meta:
        model = CircleMeetingLog
        fields = [
            "circle_id",
            "title",
            "is_report_needed",
            "report_description",
            "coord_x",
            "coord_y",
            "meet_place",
            "meet_time",
            "duration",
            "meet_link",
            "description",
            "mode",
        ]


class CircleMeetingLogListSerializer(serializers.ModelSerializer):
    circle = serializers.CharField(source="circle_id.id", read_only=True)
    created_by = serializers.CharField(source="created_by_id.full_name", read_only=True)
    is_started = serializers.SerializerMethodField()
    is_ended = serializers.SerializerMethodField()

    def get_is_started(self, obj):
        return obj.meet_time <= DateTimeUtils.get_current_utc_time()

    def get_is_ended(self, obj):
        return (obj.meet_time + timedelta(hours=obj.duration + 1)) <= datetime.now(
            timezone.utc
        )

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "circle",
            "meet_code",
            "title",
            "description",
            "mode",
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
        ]

    def get_is_member(self, obj):
        user_id = self.context.get("user_id")
        return obj.created_by_id == user_id

    def get_meet_code(self, obj):
        user_id = self.context.get("user_id")
        if not obj.created_by_id == user_id:
            return None
        return obj.meet_code

    def get_is_started(self, obj):
        return obj.meet_time <= DateTimeUtils.get_current_utc_time()

    def get_is_ended(self, obj):
        return (obj.meet_time + timedelta(hours=obj.duration + 1)) <= datetime.now(
            timezone.utc
        )

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
        if user_id:
            try:
                cur_user = (
                    User.objects.prefetch_related("user_organization_link_user")
                    .only("user_organization_link_user__org_id")
                    .get(id=user_id)
                )
                cur_user_org = cur_user.user_organization_link_user__org_id
            except:
                pass
        for attendee in query:
            data.append(
                {
                    "user_id": attendee.user_id.id,
                    "full_name": attendee.user_id.full_name,
                    "is_joined": attendee.is_joined,
                    "is_report_submitted": attendee.is_report_submitted,
                    "profile_pic": attendee.user_id.profile_pic,
                    "is_same_org": cur_user_org
                    in attendee.user_id.user_organization_link_user.all().values_list(
                        "org_id", flat=True
                    ),
                }
            )
        return data


class CircleMeetupMinSerializer(serializers.ModelSerializer):
    title = serializers.CharField(read_only=True)
    coord_x = serializers.FloatField(read_only=True)
    org = serializers.CharField(source="circle_id.org.title", read_only=True)
    coord_y = serializers.FloatField(read_only=True)
    meet_place = serializers.CharField(read_only=True)
    meet_time = serializers.DateTimeField(read_only=True)
    is_started = serializers.SerializerMethodField()
    is_ended = serializers.SerializerMethodField()
    is_joined = serializers.SerializerMethodField()
    attendees = serializers.SerializerMethodField()

    def get_is_started(self, obj):
        return obj.meet_time <= DateTimeUtils.get_current_utc_time()

    def get_is_ended(self, obj):
        return (obj.meet_time + timedelta(hours=obj.duration + 1)) <= datetime.now(
            timezone.utc
        )

    def get_is_joined(self, obj):
        if user_id := self.context.get("user_id"):
            return obj.circle_meeting_attendance_meet_id.filter(
                user_id=user_id
            ).exists()
        return False

    def get_attendees(self, obj):
        query = (
            obj.circle_meeting_attendance_meet_id.select_related("user_id")
            .prefetch_related("user_id__user_organization_link_user")
            .only(
                "user_id__full_name",
                "is_joined",
                "is_report_submitted",
                "user_id__user_organization_link_user__org_id",
            )[:3]
        )
        data = []
        user_id = self.context.get("user_id")
        cur_user_org = None
        if user_id:
            try:
                cur_user = (
                    User.objects.prefetch_related("user_organization_link_user")
                    .only("user_organization_link_user__org_id")
                    .get(id=user_id)
                )
                cur_user_org = cur_user.user_organization_link_user__org_id
            except:
                pass
        for attendee in query:
            data.append(
                {
                    "full_name": attendee.user_id.full_name,
                    "is_joined": attendee.is_joined,
                    "is_report_submitted": attendee.is_report_submitted,
                    "profile_pic": attendee.user_id.profile_pic,
                    "is_same_org": cur_user_org
                    in attendee.user_id.user_organization_link_user.all().values_list(
                        "org_id", flat=True
                    ),
                }
            )
        return data

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "title",
            "org",
            "mode",
            "meet_place",
            "coord_x",
            "coord_y",
            "meet_time",
            "is_started",
            "is_ended",
            "is_joined",
            "attendees",
        ]
