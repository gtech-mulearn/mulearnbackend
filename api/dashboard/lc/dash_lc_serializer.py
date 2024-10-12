import uuid
from datetime import datetime
from django.conf import settings
from decouple import config
from django.db.models import Sum
from rest_framework import serializers

from db.learning_circle import (
    CircleMeetAttendees,
    LearningCircle,
    UserCircleLink,
    InterestGroup,
    CircleMeetingLog,
)
from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog
from db.task import TaskList, UserIgLink, Wallet
from db.user import User
from utils.types import Lc
from utils.types import OrganizationType
from utils.utils import DateTimeUtils
from .dash_ig_helper import get_today_start_end, get_week_start_end


class LearningCircleSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.full_name")
    updated_by = serializers.CharField(source="updated_by.full_name")
    ig = serializers.CharField(source="ig.name")
    org = serializers.CharField(source="org.title", allow_null=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = [
            "id",
            "name",
            "circle_code",
            "ig",
            "org",
            "meet_place",
            "meet_time",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
            "member_count",
        ]

    def get_member_count(self, obj):
        return obj.user_circle_link_circle.filter(circle_id=obj.id, accepted=1).count()


class LearningCircleMainSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source="ig.name")
    org_name = serializers.CharField(source="org.title", allow_null=True)
    member_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    lead_name = serializers.SerializerMethodField()
    ismember = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = [
            "id",
            "name",
            "ig_name",
            "org_name",
            "member_count",
            "members",
            "meet_place",
            "meet_time",
            "lead_name",
            "ismember",
            "karma",
        ]

    def get_lead_name(self, obj):
        user_circle_link = obj.user_circle_link_circle.filter(
            circle=obj, accepted=1, lead=True
        ).first()

        return user_circle_link.user.full_name if user_circle_link else None

    def get_member_count(self, obj):
        return obj.user_circle_link_circle.filter(circle=obj, accepted=1).count()

    def get_members(self, obj):
        user_circle_link = obj.user_circle_link_circle.filter(circle=obj, accepted=1)

    def get_ismember(self, obj):
        user_id = self.context.get("user_id")
        return obj.user_circle_link_circle.filter(
            circle=obj, user_id=user_id, accepted=True
        ).exists()

        return [{"username": f"{member.user.full_name}"} for member in user_circle_link]

    def get_karma(self, obj):

        karma_activity_log = KarmaActivityLog.objects.filter(
            user__user_circle_link_user__circle=obj,
        ).aggregate(karma=Sum("karma"))["karma"]

        return karma_activity_log if karma_activity_log else 0


class LearningCircleCreateSerializer(serializers.ModelSerializer):
    ig = serializers.CharField(
        required=True, error_messages={"required": "ig field must not be left blank."}
    )
    name = serializers.CharField(
        required=True, error_messages={"required": "name field must not be left blank."}
    )

    class Meta:
        model = LearningCircle
        fields = ["name", "ig"]

    def validate(self, data):

        user_id = self.context.get("user_id")
        ig_id = data.get("ig")

        if not InterestGroup.objects.filter(id=ig_id).exists():
            raise serializers.ValidationError("Invalid interest group")

        # org_link = UserOrganizationLink.objects.filter(user_id=user_id,
        #                                                org__org_type=OrganizationType.COLLEGE.value).first()
        # if not org_link:
        #     raise serializers.ValidationError("User must be associated with a college organization")

        if UserCircleLink.objects.filter(
            user_id=user_id, circle__ig_id=ig_id, accepted=True
        ).exists():
            raise serializers.ValidationError(
                "Already a member of a learning circle with the same interest group"
            )
        return data

    def create(self, validated_data):
        user_id = self.context.get("user_id")

        org_link = UserOrganizationLink.objects.filter(
            user_id=user_id, org__org_type=OrganizationType.COLLEGE.value
        ).first()

        ig = InterestGroup.objects.filter(id=validated_data.get("ig")).first()

        if org_link:
            if len(org_link.org.code) > 4:
                code = validated_data.get("name")[:2] + ig.code + org_link.org.code[:4]
            else:
                code = validated_data.get("name")[:2] + ig.code + org_link.org.code
        else:
            code = validated_data.get("name")[:2] + ig.code

        existing_codes = set(
            LearningCircle.objects.values_list("circle_code", flat=True)
        )
        i = 1
        while code.upper() in existing_codes:
            code = code + str(i)
            i += 1
        if org_link:
            lc = LearningCircle.objects.create(
                id=uuid.uuid4(),
                name=validated_data.get("name"),
                circle_code=code.upper(),
                ig=ig,
                org=org_link.org,
                updated_by_id=user_id,
                updated_at=DateTimeUtils.get_current_utc_time(),
                created_by_id=user_id,
                created_at=DateTimeUtils.get_current_utc_time(),
            )
        else:
            lc = LearningCircle.objects.create(
                id=uuid.uuid4(),
                name=validated_data.get("name"),
                circle_code=code.upper(),
                ig=ig,
                org=None,
                updated_by_id=user_id,
                updated_at=DateTimeUtils.get_current_utc_time(),
                created_by_id=user_id,
                created_at=DateTimeUtils.get_current_utc_time(),
            )

        UserCircleLink.objects.create(
            id=uuid.uuid4(),
            user_id=user_id,
            circle=lc,
            lead=True,
            accepted=1,
            accepted_at=DateTimeUtils.get_current_utc_time(),
            created_at=DateTimeUtils.get_current_utc_time(),
        )
        return lc


# class LearningCircleMemberListSerializer(serializers.ModelSerializer):
#     members = serializers.SerializerMethodField()
#
#     class Meta:
#         model = LearningCircle
#         fields = [
#             'members',
#         ]
#
#     def get_members(self, obj):
#         # user_circle_link = obj.user_circle_link_circle.filter(circle=obj, accepted=True)
#         # return [
#         #     {
#         #         'full_name': f'{member.user.full_name}',
#         #         'discord_id': member.user.discord_id,
#         #     }
#         #     for member in user_circle_link
#         # ]
#         user_circle_link = obj.user_circle_link_circle.filter(
#             circle=obj,
#             accepted=True
#         ).values(
#             full_name=Concat(
#                 'user__full_name',
#                 Value(' '),
#                 output_field=CharField()
#             ),
#             discord_id=F('user__discord_id'),
#             level=F('user__user_lvl_link_user__level__name')
#         )
#         return user_circle_link


class LearningCircleMemberListSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name")
    discord_id = serializers.CharField(source="user.discord_id")
    level = serializers.CharField(source="user.user_lvl_link_user.level.name")
    lc_karma = serializers.SerializerMethodField()

    class Meta:
        model = UserCircleLink
        fields = ["full_name", "discord_id", "level", "lc_karma"]

    def get_lc_karma(self, obj):
        circle_id = self.context.get("circle_id")
        karma_activity_log = KarmaActivityLog.objects.filter(
            user=obj.user, task__ig__learning_circle_ig__id=circle_id
        ).aggregate(karma=Sum("karma"))["karma"]

        return karma_activity_log if karma_activity_log else 0


class LearningCircleJoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCircleLink
        fields = []

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        circle_id = self.context.get("circle_id")
        no_of_entry = UserCircleLink.objects.filter(
            circle_id=circle_id, accepted=True
        ).count()

        ig_id = LearningCircle.objects.get(pk=circle_id).ig_id

        if entry := UserCircleLink.objects.filter(
            circle_id=circle_id, user_id=user_id
        ).first():
            raise serializers.ValidationError(
                "Cannot send another request at the moment"
            )

        if UserCircleLink.objects.filter(
            user_id=user_id, circle_id__ig_id=ig_id, accepted=True
        ).exists():
            raise serializers.ValidationError(
                "Already a member of learning circle with same interest group"
            )

        if no_of_entry >= 5:
            raise serializers.ValidationError("Maximum member count reached")

        validated_data["id"] = uuid.uuid4()
        validated_data["user_id"] = user_id
        validated_data["circle_id"] = circle_id
        validated_data["lead"] = False
        validated_data["accepted"] = None
        validated_data["accepted_at"] = None
        validated_data["created_at"] = DateTimeUtils.get_current_utc_time()
        return UserCircleLink.objects.create(**validated_data)


class LearningCircleDetailsSerializer(serializers.ModelSerializer):
    college = serializers.CharField(source="org.title", allow_null=True)
    total_karma = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    pending_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    is_lead = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    ig_code = serializers.CharField(source="ig.code")
    ig_id = serializers.CharField(source="ig.id")
    ig_name = serializers.CharField(source="ig.name")
    previous_meetings = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = [
            "name",
            "circle_code",
            "note",
            "meet_time",
            "meet_place",
            "day",
            "college",
            "members",
            "pending_members",
            "rank",
            "total_karma",
            "is_lead",
            "is_member",
            "ig_id",
            "ig_name",
            "ig_code",
            "previous_meetings",
        ]

    def get_is_member(self, obj):
        user = self.context.get("user_id")
        return obj.user_circle_link_circle.filter(
            user=user, circle=obj, accepted=True
        ).exists()

    def get_is_lead(self, obj):
        user = self.context.get("user_id")
        return obj.user_circle_link_circle.filter(
            user=user, circle=obj, lead=True
        ).exists()

    def get_total_karma(self, obj):
        return (
            KarmaActivityLog.objects.filter(
                user__user_circle_link_user__circle=obj,
                user__user_circle_link_user__accepted=True,
                task__ig=obj.ig,
                appraiser_approved=True,
            ).aggregate(total_karma=Sum("karma"))["total_karma"]
            or 0
        )

    def get_members(self, obj):
        return self._get_member_info(obj, accepted=1)

    def get_pending_members(self, obj):
        return self._get_member_info(obj, accepted=None)

    def _get_member_info(self, obj, accepted):

        members = obj.user_circle_link_circle.filter(circle=obj, accepted=accepted)

        member_info = []

        for member in members:
            total_ig_karma = (
                KarmaActivityLog.objects.filter(
                    task__ig=member.circle.ig, user=member.user, appraiser_approved=True
                ).aggregate(total_karma=Sum("karma"))["total_karma"]
                or 0
            )

            member_info.append(
                {
                    "id": member.user.id,
                    "username": f"{member.user.full_name}",
                    "profile_pic": f"{member.user.profile_pic}" or None,
                    "karma": total_ig_karma,
                    "is_lead": member.lead,
                    "level": member.user.user_lvl_link_user.level.level_order,
                }
            )

        return member_info

    def get_rank(self, obj):
        total_karma = (
            KarmaActivityLog.objects.filter(
                user__user_circle_link_user__circle=obj,
                user__user_circle_link_user__accepted=True,
                task__ig=obj.ig,
                appraiser_approved=True,
            ).aggregate(total_karma=Sum("karma"))["total_karma"]
            or 0
        )

        circle_ranks = {obj.name: {"total_karma": total_karma}}

        all_learning_circles = LearningCircle.objects.filter(ig=obj.ig).exclude(
            id=obj.id
        )

        for lc in all_learning_circles:
            total_karma_lc = (
                KarmaActivityLog.objects.filter(
                    user__user_circle_link_user__circle=lc,
                    user__user_circle_link_user__accepted=True,
                    task__ig=lc.ig,
                    appraiser_approved=True,
                ).aggregate(total_karma=Sum("karma"))["total_karma"]
                or 0
            )

            circle_ranks[lc.name] = {"total_karma": total_karma_lc}

        sorted_ranks = sorted(
            circle_ranks.items(), key=lambda x: x[1]["total_karma"], reverse=True
        )

        return next(
            (
                i + 1
                for i, (circle_name, data) in enumerate(sorted_ranks)
                if circle_name == obj.name
            ),
            None,
        )

    def get_previous_meetings(self, obj):
        return (
            obj.circle_meeting_log_learning_circle.all()
            .values(
                "id",
                "meet_time",
                "day",
            )
            .order_by("-meet_time")
        )
        return previous_meetings


class LearningCircleStatsSerializer(serializers.ModelSerializer):
    interest_group = serializers.SerializerMethodField()
    college = serializers.SerializerMethodField()
    learning_circle = serializers.SerializerMethodField()
    total_no_of_users = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = ["interest_group", "college", "learning_circle", "total_no_of_users"]

    def get_interest_group(self, obj):
        return obj.values("ig_id").distinct().count()

    def get_total_no_of_users(self, obj):
        return UserCircleLink.objects.filter(accepted=True).count()

    def get_learning_circle(self, obj):
        return obj.count()

    def get_college(self, obj):
        return obj.values("org_id").distinct().count()


class LearningCircleUpdateSerializer(serializers.ModelSerializer):
    is_accepted = serializers.BooleanField()

    class Meta:
        model = UserCircleLink
        fields = ["is_accepted"]

    def update(self, instance, validated_data):
        is_accepted = validated_data.get("is_accepted", instance.accepted)
        entry = UserCircleLink.objects.filter(
            circle_id=instance.circle, accepted=True
        ).count()
        if is_accepted and entry >= 5:
            raise serializers.ValidationError(
                "Cannot accept the link. Maximum members reached for this circle."
            )

        instance.accepted = is_accepted
        instance.accepted_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def destroy(self, obj):
        obj.delete()


class LearningCircleNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField(
        required=True, error_messages={"required": "note field must not be left blank."}
    )

    class Meta:
        model = LearningCircle
        fields = ["note"]

    def update(self, instance, validated_data):
        instance.note = validated_data.get("note")
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance


class ScheduleMeetingSerializer(serializers.ModelSerializer):
    meet_time = serializers.CharField(required=True)
    day = serializers.CharField(required=True)

    class Meta:
        model = LearningCircle
        fields = ["meet_place", "meet_time", "day"]

    def update(self, instance, validated_data):
        instance.meet_time = validated_data.get("meet_time", instance.meet_time)
        instance.meet_place = validated_data.get("meet_place", instance.meet_place)
        instance.day = validated_data.get("day", instance.day)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance


class MeetRecordsCreateEditDeleteSerializer(serializers.ModelSerializer):
    images = serializers.ImageField(required=True)
    image = serializers.SerializerMethodField(required=False)
    report_text = serializers.CharField(required=True)

    class Meta:
        model = CircleMeetingLog
        fields = [
            "images",
            "image",
            "report_text",
        ]

    def get_image(self, obj):
        return (
            f"{config('BE_DOMAIN_NAME')}/{settings.MEDIA_URL}{media}"
            if (media := obj.images)
            else None
        )

    def create(self, validated_data):
        validated_data["updated_by_id"] = self.context.get("user_id")
        user = self.context.get("user")
        meet = self.context.get("meet")
        task = TaskList.objects.filter(hashtag=Lc.RECORD_SUBMIT_HASHTAG.value).first()
        attendees = (
            CircleMeetAttendees.objects.filter(
                meet=meet,
                joined_at__isnull=False,
            )
            .select_related("user")
            .only("user_id", "user__full_name")
        )
        for attendee in attendees:
            # Send karma points
            KarmaActivityLog.objects.create(
                id=uuid.uuid4(),
                user_id=attendee.user_id,
                karma=Lc.RECORD_SUBMIT_KARMA.value,
                task=task,
                updated_by=user,
                created_by=user,
                appraiser_approved=True,
                peer_approved=True,
                appraiser_approved_by=user,
                peer_approved_by=user,
                task_message_id="AUTO_APPROVED",
                lobby_message_id="AUTO_APPROVED",
                dm_message_id="AUTO_APPROVED",
            )

            wallet = Wallet.objects.filter(user_id=attendee.user_id).first()
            wallet.karma += Lc.RECORD_SUBMIT_KARMA.value
            wallet.karma_last_updated_at = DateTimeUtils.get_current_utc_time()
            wallet.updated_at = DateTimeUtils.get_current_utc_time()
            wallet.save()
        meet.is_report_submitted = True
        meet.report_text = validated_data.get("report_text")
        meet.images = validated_data.get("images")
        meet.save()
        return meet


class ListAllMeetRecordsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "meet_time",
            "day",
        ]


class IgTaskDetailsSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source="title")
    task_level = serializers.CharField(source="level.level_order")
    task_level_karma = serializers.CharField(source="level.karma")
    task_karma = serializers.CharField(source="karma")
    task_hashtag = serializers.CharField(source="hashtag")
    completed_users = serializers.SerializerMethodField()

    class Meta:
        model = TaskList
        fields = [
            "task_title",
            "task_karma",
            "task_level",
            "task_level_karma",
            "task_hashtag",
            "completed_users",
        ]

    def get_completed_users(self, obj):
        karma_activity_log = KarmaActivityLog.objects.filter(
            task=obj, appraiser_approved=True
        ).select_related("user")
        completed_users = []
        for karma in karma_activity_log:
            completed_users.append(karma.user.id)
        return completed_users


class AddMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCircleLink
        fields = []

    def validate(self, data):
        user = self.context.get("user")
        circle_id = self.context.get("circle_id")

        if UserCircleLink.objects.filter(user=user).exists():
            raise serializers.ValidationError(
                "user already part of the learning circle"
            )

        if UserCircleLink.objects.filter(circle_id=circle_id).count() >= 5:
            raise serializers.ValidationError(
                "maximum members reached in learning circle"
            )

        return data

    def create(self, validated_data):
        validated_data["id"] = uuid.uuid4()
        validated_data["user"] = self.context.get("user")
        validated_data["circle_id"] = self.context.get("circle_id")
        return UserCircleLink.objects.create(**validated_data)


class CircleMeetDetailSerializer(serializers.ModelSerializer):
    is_started = serializers.BooleanField(read_only=True)
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(required=True)
    location = serializers.CharField(required=True)
    meet_time = serializers.DateTimeField(required=True)
    meet_place = serializers.CharField(required=True)
    agenda = serializers.CharField(required=True)
    pre_requirements = serializers.CharField(required=False, allow_null=True)
    is_public = serializers.BooleanField(default=True)
    max_attendees = serializers.IntegerField(default=-1)
    report_text = serializers.CharField(required=False, allow_null=True)
    meet_code = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    is_interested = serializers.SerializerMethodField()
    joined_at = serializers.SerializerMethodField()
    total_interested = serializers.SerializerMethodField()
    total_joined = serializers.SerializerMethodField()
    lc_members = serializers.SerializerMethodField()
    is_lc_member = serializers.SerializerMethodField()

    def get_is_lc_member(self, obj):
        user_id = self.context.get("user_id")
        return UserCircleLink.objects.filter(
            user_id=user_id, circle_id=obj.circle_id, accepted=True
        ).exists()

    def get_lc_members(self, obj):
        return UserCircleLink.objects.filter(
            circle=obj.circle_id, accepted=True
        ).count()

    def get_total_interested(self, obj):
        return CircleMeetAttendees.objects.filter(meet=obj).count()

    def get_total_joined(self, obj):
        return CircleMeetAttendees.objects.filter(
            meet=obj, joined_at__isnull=False
        ).count()

    def get_is_interested(self, obj):
        user_id = self.context.get("user_id")
        return CircleMeetAttendees.objects.filter(meet=obj, user_id=user_id).exists()

    def get_joined_at(self, obj):
        user_id = self.context.get("user_id")
        return (
            CircleMeetAttendees.objects.filter(
                meet=obj, user_id=user_id, joined_at__isnull=False
            )
            .values_list("joined_at", flat=True)
            .first()
        )

    def get_meet_code(self, obj):
        if user_id := self.context.get("user_id"):
            if UserCircleLink.objects.filter(
                user_id=user_id, circle_id=obj.circle_id, accepted=True
            ).exists():
                return obj.meet_code
        return None

    def get_image(self, obj):
        return (
            f"{config('BE_DOMAIN_NAME')}/{settings.MEDIA_URL}{media}"
            if (media := obj.images)
            else None
        )

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "title",
            "location",
            "meet_time",
            "meet_place",
            "agenda",
            "pre_requirements",
            "is_public",
            "is_started",
            "max_attendees",
            "report_text",
            "meet_code",
            "image",
            "is_interested",
            "joined_at",
            "total_interested",
            "total_joined",
            "lc_members",
            "is_lc_member",
        ]


class CircleMeetSerializer(serializers.ModelSerializer):
    is_started = serializers.BooleanField(read_only=True)
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(required=True)
    location = serializers.CharField(required=True)
    meet_time = serializers.DateTimeField(required=True)
    meet_place = serializers.CharField(required=True)
    agenda = serializers.CharField(required=True)
    pre_requirements = serializers.CharField(required=False, allow_null=True)
    is_public = serializers.BooleanField(default=True)
    max_attendees = serializers.IntegerField(default=-1)
    report_text = serializers.CharField(required=False, allow_null=True)
    meet_code = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    def create(self, validated_data):
        validated_data["id"] = uuid.uuid4()
        validated_data["circle_id"] = self.context.get("circle_id")
        validated_data["created_by"] = self.context.get("user_id")
        validated_data["updated_by"] = self.context.get("user_id")
        validated_data["created_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()
        return super().create(validated_data)

    def get_meet_code(self, obj):
        if user_id := self.context.get("user_id"):
            if UserCircleLink.objects.filter(
                user_id=user_id, circle_id=obj.circle_id, accepted=True
            ).exists():
                return obj.meet_code
        return None

    def get_image(self, obj):
        return (
            f"{config('BE_DOMAIN_NAME')}/{settings.MEDIA_URL}{media}"
            if (media := obj.images)
            else None
        )

    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "title",
            "location",
            "meet_time",
            "meet_place",
            "agenda",
            "pre_requirements",
            "is_public",
            "is_started",
            "max_attendees",
            "report_text",
            "meet_code",
            "image",
        ]
