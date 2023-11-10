import uuid

from django.db.models import Sum
from rest_framework import serializers

from db.learning_circle import LearningCircle, UserCircleLink, InterestGroup, CircleMeetingLog
from db.task import TaskList
from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog
from utils.types import OrganizationType
from utils.utils import DateTimeUtils
from utils.types import Lc


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


class LearningCircleMemberListSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = [
            'members',
        ]

    def get_members(self, obj):
        user_circle_link = obj.user_circle_link_circle.filter(circle=obj, accepted=True)
        return [
            {
                'full_name': f'{member.user.fullname}',
                'discord_id': member.user.discord_id,
            }
            for member in user_circle_link
        ]


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


class LearningCircleHomeSerializer(serializers.ModelSerializer):
    college = serializers.CharField(source='org.title', allow_null=True)
    total_karma = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    pending_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    is_lead = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    ig_code = serializers.CharField(source='ig.code')
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
                'profile_pic': member.user.profile_pic or None,
                'karma': total_ig_karma,
                'is_lead': member.lead,
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


class LearningCircleCreateEditDeleteSerializer(serializers.ModelSerializer):
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


class MeetCreateEditDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = CircleMeetingLog
        fields = [
            "meet_time",
            "meet_place",
            "day",
            "attendees",
            "agenda",
        ]

    def create(self, validated_data):
        validated_data['id'] = uuid.uuid4()
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

        attendees = attendees.split(',')

        user_id = self.context.get('user_id')

        KarmaActivityLog.objects.bulk_create([
            KarmaActivityLog(
                id=uuid.uuid4(),
                user_id=user,
                karma=Lc.KARMA.value,
                task_id=task.id,
                updated_by_id=user_id,
                created_by_id=user_id,
            )
            for user in attendees
        ])

        return attendees
