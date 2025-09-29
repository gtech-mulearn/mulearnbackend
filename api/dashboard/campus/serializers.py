import uuid
from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from db.organization import Organization, UserOrganizationLink, College, CampusExecom
from db.task import KarmaActivityLog
from db.user import User, UserRoleLink
from utils.types import OrganizationType
from utils.types import RoleType
from utils.utils import DateTimeUtils


class CampusDetailsPublicSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="title")
    campus_code = serializers.ReadOnlyField(source="code")
    campus_zone = serializers.ReadOnlyField(source="district.zone.name")
    campus_level = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "college_name",
            "campus_code",
            "campus_zone",
            "campus_level",
            "total_karma",
            "total_members",
            "active_members",
            "rank",
        ]

    def get_campus_level(self, obj):
        campus = obj.college_org
        if campus:
            return campus.level

        return None

    def get_total_members(self, obj):
        return obj.user_organization_link_org.count()

    def get_active_members(self, obj):
        last_month = DateTimeUtils.get_current_utc_time() - timedelta(weeks=26)
        return obj.user_organization_link_org.filter(
            verified=True,
            user__wallet_user__isnull=False,
            user__wallet_user__karma_last_updated_at__gte=last_month,
        ).count()

    def get_total_karma(self, obj):
        return (
            obj.user_organization_link_org.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
                user__wallet_user__isnull=False,
            ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]
            or 0
        )

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .values("org")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
        ).order_by("-total_karma", "org__created_at")

        rank_dict = {
            data["org"]: data["total_karma"] if data["total_karma"] is not None else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.id)
            return position + 1


class CampusDetailsSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="org.title")
    campus_code = serializers.ReadOnlyField(source="org.code")
    campus_zone = serializers.ReadOnlyField(source="org.district.zone.name")
    campus_level = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    lead = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = [
            "college_name",
            "campus_code",
            "campus_zone",
            "campus_level",
            "total_karma",
            "total_members",
            "active_members",
            "rank",
            "lead",
        ]

    def get_lead(self, obj):

        campus_lead = User.objects.filter(
            user_organization_link_user__org=obj.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value,
        ).first()
        if campus_lead:
            campus_lead = campus_lead.full_name

        enabler = User.objects.filter(
            user_organization_link_user__org=obj.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_role_link_user__role__title=RoleType.LEAD_ENABLER.value,
        ).first()
        if enabler:
            enabler = enabler.full_name

        return {"campus_lead": campus_lead, "enabler": enabler}

    def get_campus_level(self, obj):
        campus = College.objects.filter(org=obj.org).first()
        if campus:
            return campus.level

        return None

    def get_total_members(self, obj):
        return obj.org.user_organization_link_org.count()

    def get_active_members(self, obj):

        last_month = DateTimeUtils.get_current_utc_time() - timedelta(
            weeks=26
        )  # 6months
        return obj.org.user_organization_link_org.filter(
            verified=True,
            user__wallet_user__isnull=False,
            user__wallet_user__karma_last_updated_at__gte=last_month,
        ).count()

    def get_total_karma(self, obj):
        return (
            obj.org.user_organization_link_org.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
                user__wallet_user__isnull=False,
            ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]
            or 0
        )

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.filter(
                org__org_type=OrganizationType.COLLEGE.value
            )
            .values("org")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
        ).order_by("-total_karma", "org__created_at")

        rank_dict = {
            data["org"]: data["total_karma"] if data["total_karma"] is not None else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.org.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.id)
            return position + 1


class CampusStudentDetailsSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    # is_active = serializers.CharField()
    join_date = serializers.CharField()
    last_karma_gained = serializers.CharField()
    email = serializers.CharField()
    mobile = serializers.CharField()
    graduation_year = serializers.CharField()
    department = serializers.CharField()
    is_alumni = serializers.BooleanField()

    class Meta:
        fields = (
            "user_id",
            "email",
            "mobile",
            "full_name",
            "karma",
            "muid",
            "rank",
            "level",
            "join_date",
            "is_alumni",
            "last_karma_update_at",
        )

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

    def get_full_name(self, obj):
        return obj.full_name


class WeeklyKarmaSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="title")

    class Meta:
        model = Organization
        fields = ["college_name"]

    def to_representation(self, instance):
        response = super().to_representation(instance)

        today = DateTimeUtils.get_current_utc_time().date()
        date_range = [today - timedelta(days=i) for i in range(7)]

        for date in date_range:
            karma_logs = KarmaActivityLog.objects.filter(
                user__user_organization_link_user__org=instance,
                created_at__date=date,
            ).aggregate(
                karma=Sum("karma"),
            )
            response[str(date)] = karma_logs.get("karma", 0)

        return response


class ChangeStudentTypeSerializer(serializers.Serializer):
    is_alumni = serializers.BooleanField(default=False)

    class Meta:
        model = UserOrganizationLink
        fields = ("is_alumni",)

    def update(self, instance, validated_data):
        instance.is_alumni = validated_data.get("is_alumni")
        instance.save()

        return instance


class ListAluminiSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    join_date = serializers.CharField()

    class Meta:
        fields = ("user_id", "full_name", "karma", "muid", "rank", "level", "join_date")


class UserRoleLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserRoleLink
        fields = [
            "user",
            "role",
        ]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        validated_data["verified"] = True

        user_role_link = UserRoleLink.objects.create(**validated_data)
        return user_role_link


# Campus Execom Management Serializers

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic user serializer for execom responses"""
    name = serializers.CharField(source='full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'muid']
        read_only_fields = ['id', 'name', 'email', 'muid']


class CollegeBasicSerializer(serializers.ModelSerializer):
    """Basic college serializer for execom responses"""
    name = serializers.CharField(source='org.title', read_only=True)
    code = serializers.CharField(source='org.code', read_only=True)
    
    class Meta:
        model = College
        fields = ['id', 'name', 'code']
        read_only_fields = ['id', 'name', 'code']


class CampusExecomSerializer(serializers.ModelSerializer):
    """Serializer for CampusExecom model"""
    user = UserBasicSerializer(read_only=True)
    college = CollegeBasicSerializer(read_only=True)
    user_id = serializers.CharField(write_only=True)
    college_id = serializers.CharField(write_only=True)
    added_at = serializers.DateTimeField(source='created_at', read_only=True)
    
    class Meta:
        model = CampusExecom
        fields = [
            'id', 'college', 'user', 'role', 'added_at', 
            'college_id', 'user_id'
        ]
        read_only_fields = ['id', 'added_at']
    
    def validate_role(self, value):
        """Validate role field"""
        if not value or not value.strip():
            raise serializers.ValidationError("Role cannot be empty")
        
        if len(value) > 100:
            raise serializers.ValidationError("Role name too long (max 100 characters)")
        
        return value.strip()
    
    def validate_user_id(self, value):
        """Validate that user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
    
    def validate_college_id(self, value):
        """Validate that college exists"""
        try:
            College.objects.get(id=value)
        except College.DoesNotExist:
            raise serializers.ValidationError("College not found")
        return value
    
    def validate(self, attrs):
        """Validate unique constraint"""
        college_id = attrs.get('college_id')
        user_id = attrs.get('user_id')
        role = attrs.get('role')
        
        # Check if this combination already exists
        if CampusExecom.objects.filter(
            college_id=college_id,
            user_id=user_id,
            role=role
        ).exists():
            raise serializers.ValidationError(
                "This user already has this role in this college execom"
            )
        
        return attrs
    
    def create(self, validated_data):
        """Create new execom member"""
        college = College.objects.get(id=validated_data['college_id'])
        user = User.objects.get(id=validated_data['user_id'])
        current_user = self.context.get('request').user if self.context.get('request') else None
        
        return CampusExecom.objects.create(
            college=college,
            user=user,
            role=validated_data['role'],
            created_by=current_user,
            updated_by=current_user,
            id=str(uuid.uuid4())
        )


class CampusExecomListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing execom members"""
    user_id = serializers.CharField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    added_at = serializers.DateTimeField(source='created_at', read_only=True)
    
    class Meta:
        model = CampusExecom
        fields = ['id', 'user_id', 'user_name', 'user_email', 'role', 'added_at']
        read_only_fields = ['id', 'added_at']


class UserSearchSerializer(serializers.ModelSerializer):
    """Simplified user serializer for search results"""
    name = serializers.CharField(source='full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'muid']
        read_only_fields = ['id', 'name', 'email', 'muid']
