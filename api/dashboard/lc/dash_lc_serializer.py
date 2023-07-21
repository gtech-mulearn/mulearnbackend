from rest_framework import serializers
import uuid
from db.task import InterestGroup
from db.learning_circle import LearningCircle, UserCircleLink
from db.organization import UserOrganizationLink
from utils.utils import DateTimeUtils
from utils.types import RoleType, OrganizationType
from django.db.models import Sum
from db.task import TotalKarma


class LearningCircleSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')
    ig = serializers.CharField(source='ig.name')
    org = serializers.CharField(source='org.title')
    member_count = serializers.SerializerMethodField()

    def get_member_count(self, obj):
        return UserCircleLink.objects.filter(circle_id=obj.id).count()

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


class LearningCircleCreateSerializer(serializers.ModelSerializer):
    ig = serializers.CharField(required=True, error_messages={
        'required': 'ig field must not be left blank.'
    })
    name = serializers.CharField(required=True,error_messages={
        'required': 'name field must not be left blank.'}
                                 )

    class Meta:
        model = LearningCircle
        fields = [
            "name",
            "ig",
            "circle_code",
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        org_link = UserOrganizationLink.objects.filter(user_id=user_id,
                                                       org__org_type=OrganizationType.COLLEGE.value).first()
        ig = InterestGroup.objects.filter(id=validated_data.get('ig')).first()

        lc = LearningCircle.objects.create(
            id=uuid.uuid4(),
            name=validated_data.get('name'),
            circle_code=validated_data.get('circle_code'),
            ig=ig,
            org=org_link.org,
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
            created_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time())

        UserCircleLink.objects.create(
            id=uuid.uuid4(),
            user=org_link.user,
            circle=lc,
            lead=True,
            accepted=1,
            accepted_at=DateTimeUtils.get_current_utc_time(),
            created_at=DateTimeUtils.get_current_utc_time()
        )
        return lc


class LearningCircleHomeSerializer(serializers.ModelSerializer):
    college = serializers.CharField(source='org.title')
    total_karma = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    pending_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    def get_total_karma(self, obj):
        return TotalKarma.objects.filter(user__usercirclelink__circle=obj).aggregate(total_karma=Sum('karma'))[
            'total_karma'] or 0

    def get_members(self, obj):
        members = UserCircleLink.objects.filter(circle=obj, accepted=1)
        return [
            {'id': member.user.id,
             'username': f'{member.user.first_name} {member.user.last_name}'
             if member.user.last_name
             else member.user.first_name,
             'profile_pic': member.user.profile_pic or None,
             'karma': TotalKarma.objects.filter(user=member.user.id)
             .values_list('karma', flat=True)
             .first(),
             }
            for member in members
        ]

    def get_pending_members(self, obj):
        pending_members = UserCircleLink.objects.filter(circle=obj, accepted=0)
        return [
            {
                'id': member.user.id,
                'username': f'{member.user.first_name} {member.user.last_name}'
                if member.user.last_name
                else member.user.first_name,
                'profile_pic': member.user.profile_pic or None,
            }
            for member in pending_members
        ]

    def get_rank(self, obj):
        return 3

    class Meta:
        model = LearningCircle
        fields = [
            "name",
            "circle_code",
            "college",
            "members",
            "pending_members",
            "rank",
            "total_karma"
        ]


class LearningCircleUpdateSerializer(serializers.ModelSerializer):
    is_accepted = serializers.BooleanField()

    class Meta:
        model = UserCircleLink
        fields = [
            "is_accepted"
        ]

    def update(self, instance, validated_data):
        instance.accepted = validated_data.get('is_accepted', instance.accepted)
        instance.accepted_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance
