import uuid
from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from db.organization import Organization, UserOrganizationLink, College
from db.task import KarmaActivityLog, InterestGroup, UserIgLink
from db.campus import CampusIGChapter, CampusSocialLink
from db.user import User, UserRoleLink
from utils.types import OrganizationType
from utils.types import RoleType, SocialPlatformType
from utils.utils import DateTimeUtils
from .dash_campus_helper import validate_campus_member, assign_ig_campus_lead
from db.events import Event

class CampusDetailsPublicSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="title")
    campus_code = serializers.ReadOnlyField(source="code")
    campus_zone = serializers.ReadOnlyField(source="district.zone.name")
    campus_level = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
   
    

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
            "social_links",
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

    def get_social_links(self, obj):
        links = CampusSocialLink.objects.filter(org=obj)
        return CampusSocialLinkSerializer(links, many=True).data



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
    karma_last_7_days = serializers.SerializerMethodField()
    karma_last_30_days = serializers.SerializerMethodField()
    active_ig_count = serializers.SerializerMethodField()
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
            "karma_last_7_days",
            "karma_last_30_days",
            "active_ig_count",
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
    def get_karma_last_7_days(self, obj):
        seven_days_ago = DateTimeUtils.get_current_utc_time() - timedelta(days=7)
        return (
            KarmaActivityLog.objects.filter(
                user__user_organization_link_user__org=obj.org,
                created_at__gte=seven_days_ago,
            ).aggregate(total_karma=Sum("karma"))["total_karma"] or 0
        )

    def get_karma_last_30_days(self, obj):
        thirty_days_ago = DateTimeUtils.get_current_utc_time() - timedelta(days=30)
        return (
            KarmaActivityLog.objects.filter(
                user__user_organization_link_user__org=obj.org,
                created_at__gte=thirty_days_ago,
            ).aggregate(total_karma=Sum("karma"))["total_karma"] or 0
        )
    def get_active_ig_count(self, obj):
        return (
            InterestGroup.objects.filter(
                user_ig_link_ig__user__user_organization_link_user__org=obj.org,
                user_ig_link_ig__user__user_organization_link_user__verified=True,
                status="active",
            )
            .distinct()
            .count()
        )


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


class CampusEventListSerializer(serializers.ModelSerializer):
    tags = serializers.JSONField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "status",
            "scope",
            "organiser_type",
            "start_datetime",
            "end_datetime",
            "venue_type",
            "venue_city",
            "interest_count",
            "cover_image",
            "tags",
        ]


class ExecomMemberSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    muid = serializers.CharField(source="user.muid")
    profile_pic = serializers.SerializerMethodField()
    role_title = serializers.CharField(source="role.title")
    ig_name = serializers.SerializerMethodField()

    class Meta:
        model = UserRoleLink
        fields = [
            "user_id",
            "full_name",
            "muid",
            "profile_pic",
            "role_title",
            "ig_name",
        ]

    def get_profile_pic(self, obj):
        return str(obj.user.profile_pic) if obj.user.profile_pic else None

    def get_ig_name(self, obj):
        title = obj.role.title
        # IG campus lead roles end with 'CampusLead'
        # Handles both 'pythonCampusLead' and 'WEBDEV CampusLead'
        if title not in (
            RoleType.CAMPUS_LEAD.value,
            RoleType.LEAD_ENABLER.value,
        ) and title.endswith("CampusLead"):
            ig_name = title.replace("CampusLead", "").strip()
            return ig_name or None
        return None

    # get_rank and get_full_name are inherited from CampusStudentDetailsSerializer


class CampusIGChapterListSerializer(serializers.ModelSerializer):
    ig_id = serializers.ReadOnlyField(source="ig.id")
    ig_name = serializers.ReadOnlyField(source="ig.name")
    ig_code = serializers.ReadOnlyField(source="ig.code")
    ig_icon = serializers.ReadOnlyField(source="ig.icon")
    lead_id = serializers.ReadOnlyField(source="lead.id")
    lead_name = serializers.SerializerMethodField()
    campus_ig_member_count = serializers.SerializerMethodField()

    class Meta:
        model = CampusIGChapter
        fields = [
            "id",
            "ig_id",
            "ig_name",
            "ig_code",
            "ig_icon",
            "lead_id",
            "lead_name",
            "description",
            "is_active",
            "campus_ig_member_count",
        ]

    def get_lead_name(self, obj):
        if obj.lead:
            return obj.lead.full_name
        return None

    def get_campus_ig_member_count(self, obj):
        return UserIgLink.objects.filter(
            ig=obj.ig,
            user__user_organization_link_user__org=obj.org,
        ).count()


class CampusIGChapterCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampusIGChapter
        fields = ["ig", "description", "lead"]

    def validate_ig(self, value):
        org = self.context.get("org")
        if CampusIGChapter.objects.filter(org=org, ig=value, is_active=True).exists():
            raise serializers.ValidationError("An active IG chapter already exists for this campus and IG.")
        return value

    def validate_lead(self, value):
        if value is None:
            return value
        org = self.context.get("org")
        if not validate_campus_member(value.id, org.id):
            raise serializers.ValidationError("The lead must be a member of this campus.")
        return value

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        org = self.context.get("org")
        validated_data["id"] = str(uuid.uuid4())
        validated_data["org"] = org
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id

        chapter = CampusIGChapter.objects.create(**validated_data)

        # Assign campus IG lead role if lead is provided
        if chapter.lead:
            assign_ig_campus_lead(chapter, chapter.lead, user_id)

        return chapter


class CampusIGChapterUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampusIGChapter
        fields = ["description", "lead", "is_active"]

    def validate_lead(self, value):
        if value is None:
            return value
        org = self.instance.org
        if not validate_campus_member(value.id, org.id):
            raise serializers.ValidationError("The lead must be a member of this campus.")
        return value

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        new_lead = validated_data.get("lead")

        instance.description = validated_data.get("description", instance.description)
        instance.is_active = validated_data.get("is_active", instance.is_active)
        instance.updated_by_id = user_id

        # If lead changed, reassign campus IG lead role
        if new_lead and new_lead != instance.lead:
            assign_ig_campus_lead(instance, new_lead, user_id)
        else:
            instance.save()

        return instance


class CampusSocialLinkSerializer(serializers.ModelSerializer):

    class Meta:
        model = CampusSocialLink
        fields = ["id", "platform", "url"]


class CampusSocialLinkUpsertSerializer(serializers.Serializer):
    platform = serializers.CharField(max_length=30)
    url = serializers.URLField(max_length=500)

    def validate_platform(self, value):
        if value not in SocialPlatformType.get_all_values():
            raise serializers.ValidationError(
                f"Invalid platform. Must be one of: {', '.join(SocialPlatformType.get_all_values())}"
            )
        return value

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        org = self.context.get("org")

        try:
            social_link = CampusSocialLink.objects.get(
                org=org,
                platform=validated_data["platform"],
            )
            social_link.url = validated_data["url"]
            social_link.updated_by_id = user_id
            social_link.save()
        except CampusSocialLink.DoesNotExist:
            social_link = CampusSocialLink.objects.create(
                id=str(uuid.uuid4()),
                org=org,
                platform=validated_data["platform"],
                url=validated_data["url"],
                created_by_id=user_id,
                updated_by_id=user_id,
            )
        return social_link
