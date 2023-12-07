import uuid
from datetime import datetime
from django.conf import settings
from decouple import config
from django.db.models import Sum
from rest_framework import serializers

from db.learning_circle import LearningCircle, UserCircleLink, InterestGroup, CircleMeetingLog
from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog
from db.task import TaskList, UserIgLink, Wallet
from db.user import User
from utils.types import Lc
from utils.types import OrganizationType
from utils.utils import DateTimeUtils
from .dash_ig_helper import get_today_start_end, get_week_start_end


class LearningCircleSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')
    ig = serializers.CharField(source='ig.name')
    org = serializers.CharField(source='org.title', allow_null=True)
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
        return obj.user_circle_link_circle.filter(
            circle_id=obj.id,
            accepted=1
        ).count()


class LearningCircleMainSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source='ig.name')
    member_count = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    lead_name = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = [
            'name',
            'ig_name',
            'member_count',
            'members',
            'meet_place',
            'meet_time',
            'lead_name'
        ]

    def get_lead_name(self, obj):
        user_circle_link = obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=1,
            lead=True
        ).first()

        return user_circle_link.user.fullname if user_circle_link else None

    def get_member_count(self, obj):
        return obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=1
        ).count()

    def get_members(self, obj):
        user_circle_link = obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=1
        )
        return [
            {
                'username': f'{member.user.fullname}'
            }
            for member in user_circle_link
        ]


class LearningCircleCreateSerializer(serializers.ModelSerializer):
    ig = serializers.CharField(required=True, error_messages={
        'required': 'ig field must not be left blank.'
    })
    name = serializers.CharField(required=True, error_messages={
        'required': 'name field must not be left blank.'}
                                 )

    class Meta:
        model = LearningCircle
        fields = [
            "name",
            "ig"
        ]

    def validate(self, data):

        user_id = self.context.get('user_id')
        ig_id = data.get('ig')

        if not InterestGroup.objects.filter(
                id=ig_id
        ).exists():
            raise serializers.ValidationError(
                "Invalid interest group"
            )

        # org_link = UserOrganizationLink.objects.filter(user_id=user_id,
        #                                                org__org_type=OrganizationType.COLLEGE.value).first()
        # if not org_link:
        #     raise serializers.ValidationError("User must be associated with a college organization")

        if UserCircleLink.objects.filter(
                user_id=user_id,
                circle__ig_id=ig_id,
                accepted=True
        ).exists():
            raise serializers.ValidationError(
                "Already a member of a learning circle with the same interest group"
            )
        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')

        org_link = UserOrganizationLink.objects.filter(
            user_id=user_id,
            org__org_type=OrganizationType.COLLEGE.value
        ).first()

        ig = InterestGroup.objects.filter(
            id=validated_data.get(
                'ig'
            )
        ).first()

        if org_link:
            if len(org_link.org.code) > 4:
                code = validated_data.get('name')[:2] + ig.code + org_link.org.code[:4]
            else:
                code = validated_data.get('name')[:2] + ig.code + org_link.org.code
        else:
            code = validated_data.get('name')[:2] + ig.code

        existing_codes = set(LearningCircle.objects.values_list('circle_code', flat=True))
        i = 1
        while code.upper() in existing_codes:
            code = code + str(i)
            i += 1
        if org_link:
            lc = LearningCircle.objects.create(
                id=uuid.uuid4(),
                name=validated_data.get('name'),
                circle_code=code.upper(),
                ig=ig,
                org=org_link.org,
                updated_by_id=user_id,
                updated_at=DateTimeUtils.get_current_utc_time(),
                created_by_id=user_id,
                created_at=DateTimeUtils.get_current_utc_time())
        else:
            lc = LearningCircle.objects.create(
                id=uuid.uuid4(),
                name=validated_data.get('name'),
                circle_code=code.upper(),
                ig=ig,
                org=None,
                updated_by_id=user_id,
                updated_at=DateTimeUtils.get_current_utc_time(),
                created_by_id=user_id,
                created_at=DateTimeUtils.get_current_utc_time())

        UserCircleLink.objects.create(
            id=uuid.uuid4(),
            user_id=user_id,
            circle=lc,
            lead=True,
            accepted=1,
            accepted_at=DateTimeUtils.get_current_utc_time(),
            created_at=DateTimeUtils.get_current_utc_time()
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
#         #         'full_name': f'{member.user.fullname}',
#         #         'discord_id': member.user.discord_id,
#         #     }
#         #     for member in user_circle_link
#         # ]
#         user_circle_link = obj.user_circle_link_circle.filter(
#             circle=obj,
#             accepted=True
#         ).values(
#             full_name=Concat(
#                 'user__first_name',
#                 Value(' '),
#                 'user__last_name',
#                 output_field=CharField()
#             ),
#             discord_id=F('user__discord_id'),
#             level=F('user__user_lvl_link_user__level__name')
#         )
#         return user_circle_link

class LearningCircleMemberListSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source='user.fullname')
    discord_id = serializers.CharField(source='user.discord_id')
    level = serializers.CharField(source='user.user_lvl_link_user.level.name')
    lc_karma = serializers.SerializerMethodField()

    class Meta:
        model = UserCircleLink
        fields = [
            'fullname',
            'discord_id',
            'level',
            'lc_karma'
        ]

    def get_lc_karma(self, obj):
        circle_id = self.context.get('circle_id')
        karma_activity_log = KarmaActivityLog.objects.filter(
            user=obj.user,
            task__ig__learning_circle_ig__id=circle_id
        ).aggregate(
            karma=Sum(
                'karma'
            )
        )['karma']

        return karma_activity_log if karma_activity_log else 0


class LearningCircleJoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCircleLink
        fields = []

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        circle_id = self.context.get('circle_id')
        no_of_entry = UserCircleLink.objects.filter(
            circle_id=circle_id,
            accepted=True
        ).count()

        ig_id = LearningCircle.objects.get(pk=circle_id).ig_id

        if entry := UserCircleLink.objects.filter(
                circle_id=circle_id,
                user_id=user_id
        ).first():
            raise serializers.ValidationError(
                "Cannot send another request at the moment"
            )

        if UserCircleLink.objects.filter(
                user_id=user_id,
                circle_id__ig_id=ig_id,
                accepted=True
        ).exists():
            raise serializers.ValidationError(
                "Already a member of learning circle with same interest group"
            )

        if no_of_entry >= 5:
            raise serializers.ValidationError(
                "Maximum member count reached"
            )

        validated_data['id'] = uuid.uuid4()
        validated_data['user_id'] = user_id
        validated_data['circle_id'] = circle_id
        validated_data['lead'] = False
        validated_data['accepted'] = None
        validated_data['accepted_at'] = None
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
        return UserCircleLink.objects.create(**validated_data)


class LearningCircleDetailsSerializer(serializers.ModelSerializer):
    college = serializers.CharField(source='org.title', allow_null=True)
    total_karma = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    pending_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    is_lead = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    ig_code = serializers.CharField(source='ig.code')
    ig_id = serializers.CharField(source='ig.id')
    ig_name = serializers.CharField(source='ig.name')
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
        user = self.context.get('user_id')
        return obj.user_circle_link_circle.filter(
            user=user,
            circle=obj,
            accepted=True
        ).exists()

    def get_is_lead(self, obj):
        user = self.context.get('user_id')
        return obj.user_circle_link_circle.filter(
            user=user,
            circle=obj,
            lead=True
        ).exists()

    def get_total_karma(self, obj):
        return (
                KarmaActivityLog.objects.filter(
                    user__user_circle_link_user__circle=obj,
                    user__user_circle_link_user__accepted=True,
                    task__ig=obj.ig,
                    appraiser_approved=True,
                ).aggregate(
                    total_karma=Sum(
                        'karma'
                    ))['total_karma'] or 0
        )

    def get_members(self, obj):
        return self._get_member_info(obj, accepted=1)

    def get_pending_members(self, obj):
        return self._get_member_info(obj, accepted=None)

    def _get_member_info(self, obj, accepted):

        members = obj.user_circle_link_circle.filter(
            circle=obj,
            accepted=accepted
        )

        member_info = []

        for member in members:
            total_ig_karma = KarmaActivityLog.objects.filter(
                task__ig=member.circle.ig,
                user=member.user,
                appraiser_approved=True
            ).aggregate(
                total_karma=Sum(
                    'karma'
                ))['total_karma'] or 0

            member_info.append({
                'id': member.user.id,
                'username': f'{member.user.fullname}',
                'profile_pic': f'{member.user.profile_pic}' or None,
                'karma': total_ig_karma,
                'is_lead': member.lead,
                'level': member.user.user_lvl_link_user.level.level_order
            })

        return member_info

    def get_rank(self, obj):
        total_karma = KarmaActivityLog.objects.filter(
            user__user_circle_link_user__circle=obj,
            user__user_circle_link_user__accepted=True,
            task__ig=obj.ig,
            appraiser_approved=True
        ).aggregate(
            total_karma=Sum(
                'karma'
            )
        )['total_karma'] or 0

        circle_ranks = {obj.name: {'total_karma': total_karma}}

        all_learning_circles = LearningCircle.objects.filter(
            ig=obj.ig
        ).exclude(
            id=obj.id
        )

        for lc in all_learning_circles:
            total_karma_lc = KarmaActivityLog.objects.filter(
                user__user_circle_link_user__circle=lc,
                user__user_circle_link_user__accepted=True,
                task__ig=lc.ig,
                appraiser_approved=True
            ).aggregate(
                total_karma=Sum(
                    'karma'
                )
            )['total_karma'] or 0

            circle_ranks[lc.name] = {'total_karma': total_karma_lc}

        sorted_ranks = sorted(
            circle_ranks.items(),
            key=lambda x: x[1]['total_karma'],
            reverse=True
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
        return obj.circle_meeting_log_learning_circle.all().values(
            "id",
            "meet_time",
            "day",
        ).order_by(
            '-meet_time'
        )
        return previous_meetings


class LearningCircleDataSerializer(serializers.ModelSerializer):
    interest_group = serializers.SerializerMethodField()
    college = serializers.SerializerMethodField()
    learning_circle = serializers.SerializerMethodField()
    total_no_of_users = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = [
            "interest_group",
            "college",
            "learning_circle",
            "total_no_of_users"
        ]

    def get_interest_group(self, obj):
        return obj.values('ig_id').distinct().count()

    def get_total_no_of_users(self, obj):
        return UserCircleLink.objects.all().count()

    def get_learning_circle(self, obj):
        return obj.count()

    def get_college(self, obj):
        return obj.values('org_id').distinct().count()


class LearningCircleUpdateSerializer(serializers.ModelSerializer):
    is_accepted = serializers.BooleanField()

    class Meta:
        model = UserCircleLink
        fields = [
            "is_accepted"
        ]

    def update(self, instance, validated_data):
        is_accepted = validated_data.get('is_accepted', instance.accepted)
        entry = UserCircleLink.objects.filter(circle_id=instance.circle, accepted=True).count()
        if is_accepted and entry >= 5:
            raise serializers.ValidationError("Cannot accept the link. Maximum members reached for this circle.")

        instance.accepted = is_accepted
        instance.accepted_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def destroy(self, obj):
        obj.delete()


class LearningCircleNoteSerializer(serializers.ModelSerializer):
    note = serializers.CharField(required=True, error_messages={
        'required': 'note field must not be left blank.'
    })

    class Meta:
        model = LearningCircle
        fields = [
            "note"
        ]

    def update(self, instance, validated_data):
        instance.note = validated_data.get('note')
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance


class ScheduleMeetingSerializer(serializers.ModelSerializer):
    meet_time = serializers.CharField(required=True)
    day = serializers.CharField(required=True)

    class Meta:
        model = LearningCircle
        fields = [
            "meet_place",
            "meet_time",
            "day"
        ]

    def update(self, instance, validated_data):
        instance.meet_time = validated_data.get('meet_time', instance.meet_time)
        instance.meet_place = validated_data.get('meet_place', instance.meet_place)
        instance.day = validated_data.get('day', instance.day)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance


class MeetRecordsCreateEditDeleteSerializer(serializers.ModelSerializer):
    attendees_details = serializers.SerializerMethodField()
    meet_created_by = serializers.CharField(source='created_by.fullname', required=False)
    meet_created_at = serializers.CharField(source='created_at', required=False)
    meet_id = serializers.CharField(source='id', required=False)
    meet_time = serializers.CharField(required=False)
    images = serializers.ImageField(required=True)
    image = serializers.SerializerMethodField(required=False)

    class Meta:
        model = CircleMeetingLog
        fields = [
            "meet_id",
            "meet_place",
            "meet_time",
            "images",
            "attendees",
            "agenda",
            "attendees_details",
            "meet_created_by",
            "meet_created_at",
            'image',
        ]

    def get_image(self, obj):
        return f"{config('BE_DOMAIN_NAME')}/{settings.MEDIA_URL}{media}" if (media := obj.images) else None
    def get_attendees_details(self, obj):
        attendees_list = obj.attendees.split(',')

        attendees_details_list = []
        for user_id in attendees_list:
            user = User.objects.get(id=user_id)
            attendees_details_list.append({
                'fullname': user.fullname,
                'profile_pic': user.profile_pic,
            })

        return attendees_details_list

    def create(self, validated_data):
        today_date = DateTimeUtils.get_current_utc_time().date()
        meet_time_string = self.context.get('time')
        meet_time = datetime.strptime(meet_time_string, "%H:%M:%S").time()

        combined_meet_time = datetime.combine(today_date, meet_time)

        validated_data['id'] = uuid.uuid4()
        validated_data['meet_time'] = combined_meet_time
        validated_data['day'] = DateTimeUtils.get_current_utc_time().strftime('%A')
        validated_data['circle_id'] = self.context.get('circle_id')
        validated_data['created_by_id'] = self.context.get('user_id')
        validated_data['updated_by_id'] = self.context.get('user_id')
        return CircleMeetingLog.objects.create(**validated_data)

    def update(self, instance, validated_data):
        instance.updated_by_id = self.context.get('user_id')
        instance.save()
        return instance

    def validate_attendees(self, attendees):
        task = TaskList.objects.filter(hashtag=Lc.TASK_HASHTAG.value).first()

        attendees_list = attendees.split(',')

        user_id = self.context.get('user_id')
        for user in attendees_list:
            KarmaActivityLog.objects.bulk_create([
                KarmaActivityLog(
                    id=uuid.uuid4(),
                    user_id=user,
                    karma=Lc.KARMA.value,
                    task=task,
                    updated_by_id=user_id,
                    created_by_id=user_id,
                )
            ])
            wallet = Wallet.objects.filter(user_id=user).first()
            wallet.karma += Lc.KARMA.value
            wallet.karma_last_updated_at = DateTimeUtils.get_current_utc_time()
            wallet.updated_at = DateTimeUtils.get_current_utc_time()
            wallet.save()
        return attendees

    def validate(self, data):
        circle_id = self.context.get('circle_id')

        today_date = DateTimeUtils.get_current_utc_time().date()
        time = self.context.get('time')
        time = datetime.strptime(time, "%H:%M:%S").time()
        combined_meet_time = datetime.combine(today_date, time)

        start_of_day, end_of_day = get_today_start_end(combined_meet_time)
        start_of_week, end_of_week = get_week_start_end(combined_meet_time)

        if CircleMeetingLog.objects.filter(
                circle_id=circle_id,
                meet_time__range=(
                        start_of_day,
                        end_of_day
                )
        ).exists():
            raise serializers.ValidationError(f'Another meet already scheduled on {today_date}')

        if CircleMeetingLog.objects.filter(
                circle_id=circle_id,
                meet_time__range=(
                        start_of_week,
                        end_of_week
                )
        ).count() >= 5:
            raise serializers.ValidationError('you can create only 5 meeting in a week')

        return data


class ListAllMeetRecordsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircleMeetingLog
        fields = [
            "id",
            "meet_time",
            "day",
        ]


class IgTaskDetailsSerializer(serializers.ModelSerializer):
    task = serializers.CharField(source='title')
    task_status = serializers.SerializerMethodField()
    task_id = serializers.CharField(source='id')
    task_level = serializers.CharField(source='level.level_order')
    task_level_karma = serializers.CharField(source='level.karma')
    task_karma = serializers.CharField(source='karma')
    task_description = serializers.CharField(source='description')
    interest_group = serializers.CharField(source='ig.name')

    class Meta:
        model = TaskList
        fields = [
            "task_id",
            "task",
            "task_karma",
            "task_description",
            "interest_group",
            "task_status",
            "task_level",
            "task_level_karma",
        ]

    def get_task_status(self, obj):
        user_ig_links = UserIgLink.objects.filter(ig=obj.ig).select_related('user')
        for user_ig_link in user_ig_links:
            if obj.karma_activity_log_task.filter(
                    user=user_ig_link.user,
                    peer_approved=True).exists():
                return True
            else:
                return False


class AddMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCircleLink
        fields = []

    def validate(self, data):
        user = self.context.get('user')
        circle_id = self.context.get('circle_id')

        if UserCircleLink.objects.filter(user=user).exists():
            raise serializers.ValidationError('user already part of the learning circle')

        if UserCircleLink.objects.filter(circle_id=circle_id).count() >= 5:
            raise serializers.ValidationError('maximum members reached in learning circle')

        return data

    def create(self, validated_data):
        validated_data['id'] = uuid.uuid4()
        validated_data['user'] = self.context.get('user')
        validated_data['circle_id'] = self.context.get('circle_id')
        return UserCircleLink.objects.create(**validated_data)
