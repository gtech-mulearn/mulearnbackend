import uuid

from django.db.models import Sum
from rest_framework import serializers

from db.learning_circle import LearningCircle, UserCircleLink, InterestGroup
from db.organization import UserOrganizationLink
from db.task import TotalKarma
from utils.types import OrganizationType
from utils.utils import DateTimeUtils


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
    name = serializers.CharField(required=True, error_messages={
        'required': 'name field must not be left blank.'}
                                 )

    class Meta:
        model = LearningCircle
        fields = [
            "name",
            "ig"
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        org_link = UserOrganizationLink.objects.filter(user_id=user_id,
                                                       org__org_type=OrganizationType.COLLEGE.value).first()
        ig = InterestGroup.objects.filter(id=validated_data.get('ig')).first()
        code = org_link.org.code + ig.code + validated_data.get('name').upper()[:2]
        existing_codes = set(LearningCircle.objects.values_list('circle_code', flat=True))
        i = 1
        while code in existing_codes:
            code = org_link.org.code + ig.code + validated_data.get('name').upper()[:2] + str(i)
            i += 1

        lc = LearningCircle.objects.create(
            id=uuid.uuid4(),
            name=validated_data.get('name'),
            circle_code=code,
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
    is_lead = serializers.SerializerMethodField()

    def get_is_lead(self, obj):
        user = self.context.get('user_id')
        try:
            if link := UserCircleLink.objects.get(
                user=user, circle=obj, lead=True
            ):
                return True
        except UserCircleLink.DoesNotExist:
            return False

    def get_total_karma(self, obj):
        return TotalKarma.objects.filter(user__usercirclelink__circle=obj,user__usercirclelink__accepted=1).aggregate(
            total_karma=Sum('karma'))[
                   'total_karma'] or 0

    def get_members(self, obj):
        return self._get_member_info(obj, accepted=1)

    def get_pending_members(self, obj):
        return self._get_member_info(obj, accepted=None)

    def _get_member_info(self, obj, accepted):
        members = UserCircleLink.objects.filter(circle=obj, accepted=accepted)
        return [
            {
                'id': member.user.id,
                'username': f'{member.user.first_name} {member.user.last_name}' if member.user.last_name else member.user.first_name,
                'profile_pic': member.user.profile_pic or None,
                'karma': TotalKarma.objects.filter(user=member.user.id).values_list('karma', flat=True).first(),
            }
            for member in members
        ]

    def get_rank(self, obj):
        rank = UserCircleLink.objects.filter(user__usercirclelink__circle=obj, accepted=True,
                                             user__total_karma_user__isnull=False).values('circle_id').annotate(
            total_karma=Sum('user__total_karma_user__karma')
        ).order_by('-total_karma')
        lc_rank = {lc['circle_id']: i + 1 for i, lc in enumerate(rank)}
        return lc_rank.get(obj.id)

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
            "is_lead"
        ]


class LearningCircleJoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCircleLink
        fields = []

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        circle_id = self.context.get('circle_id')
        no_of_entry = UserCircleLink.objects.filter(circle_id=circle_id, accepted=True).count()
        ig_id = LearningCircle.objects.get(pk=circle_id).ig_id
        if entry := UserCircleLink.objects.filter(
                circle_id=circle_id, user_id=user_id
        ).first():
            raise serializers.ValidationError("Cannot send another request at the moment")
        if UserCircleLink.objects.filter(user_id=user_id, circle_id__ig_id=ig_id, accepted=True).exists():
            raise serializers.ValidationError("Already a member of learning circle with same interest group")
        if no_of_entry >= 5:
            raise serializers.ValidationError("Maximum member count reached")

        validated_data['id'] = uuid.uuid4()
        validated_data['user_id'] = user_id
        validated_data['circle_id'] = circle_id
        validated_data['lead'] = False
        validated_data['accepted'] = None
        validated_data['accepted_at'] = None
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
        return UserCircleLink.objects.create(**validated_data)


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


class LearningCircleMeetSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningCircle
        fields = [
            "meet_place",
            "meet_time",
            "day"
        ]

    def update(self, instance, validated_data):
        instance.meet_time = validated_data.get('meet_time')
        instance.meet_place = validated_data.get('meet_place')
        instance.day = validated_data.get('date')
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance


class LearningCircleMainSerializer(serializers.ModelSerializer):
    ig_name = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = LearningCircle
        fields = ['name', 'ig_name', 'member_count']

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None

    def get_member_count(self, obj):
        return UserCircleLink.objects.filter(circle=obj, accepted=True).count()
