from datetime import timedelta

from django.db.models import Sum, F
from rest_framework import serializers

from db.organization import UserOrganizationLink, District, Organization, College
from db.task import KarmaActivityLog, Level, UserLvlLink, TotalKarma
from db.user import User
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class ZonalDetailsSerializer(serializers.ModelSerializer):
    zone = serializers.CharField(source="org.district.zone.name")
    rank = serializers.SerializerMethodField()
    zonal_lead = serializers.CharField(source="user.fullname")
    karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = [
            "zone",
            "rank",
            "zonal_lead",
            "karma",
            "total_members",
            "active_members",
        ]

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.all()
            .values("org__district__zone")
            .annotate(total_karma=Sum("user__total_karma_user__karma"))
        )

        rank_dict = {
            data["org__district__zone"]: data["total_karma"]
            if data["total_karma"] is not None
            else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.org.district.zone.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.district.zone.id)
            return position + 1

    def get_karma(self, obj):
        return UserOrganizationLink.objects.filter(
            org__district__zone=obj.org.district.zone,
        ).aggregate(total_karma=Sum("user__total_karma_user__karma"))["total_karma"]

    def get_total_members(self, obj):
        return UserOrganizationLink.objects.filter(
            org__district__zone=obj.org.district.zone,
        ).count()

    def get_active_members(self, obj):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(
            day=1, month=(start_date.month % 12) + 1
        ) - timedelta(days=1)

        return KarmaActivityLog.objects.filter(
            user__user_organization_link_user_id__org__district__zone=obj.org.district.zone,
            created_at__range=(start_date, end_date),
        ).count()


class ZonalTopThreeDistrictSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source="name")
    rank = serializers.SerializerMethodField()
    
    def get_rank(self, district):
        keys_list = list(self.context("ranks").keys())
        position = keys_list.index(district.org.district.zone.id)
        return position + 1
        
    
    class Meta:
        model = District
        fields = ["district", "id", "rank"] 


class ZonalStudentLevelStatusSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source="title")
    college_code = serializers.CharField(source="code")
    level = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["college_name", "college_code", "level"]

    def get_level(self, obj):
        level = Level.objects.all()
        level_dict = {}
        level_list = []
        for levels in level:
            level_dict["level"] = levels.level_order
            level_dict["students_count"] = len(
                UserLvlLink.objects.filter(
                    level=levels,
                    user__user_organization_link_user_id=obj.user_organization_link_org_id,
                ).all()
            )
            level_list.append(level_dict)
            level_dict = {}
        return level_list


class UserOrgSerializer(serializers.ModelSerializer):
    fullname = serializers.ReadOnlyField(source="user.fullname")
    muid = serializers.ReadOnlyField(source="user.mu_id")
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ("fullname", "karma", "muid", "rank", "level", "created_at")

    def get_karma(self, obj):
        return obj.user.total_karma_user.karma or 0

    def get_rank(self, obj):
        rank = (
            TotalKarma.objects.filter(user__total_karma_user__isnull=False)
            .annotate(rank=F("user__total_karma_user__karma"))
            .order_by("-rank")
            .values_list("rank", flat=True)
        )

        ranks = {karma: i + 1 for i, karma in enumerate(rank)}
        return ranks.get(obj.user.total_karma_user.karma, None)

    def get_level(self, obj):
        user_level_link = UserLvlLink.objects.filter(user=obj.user).first()
        if user_level_link:
            return user_level_link.level.name
        return None


class ZonalStudentDetailsSerializer(serializers.ModelSerializer):
    fullname = serializers.ReadOnlyField(source="user.fullname")
    muid = serializers.ReadOnlyField(source="user.mu_id")
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ("fullname", "karma", "muid", "rank", "level", "created_at")

    def get_karma(self, obj):
        return obj.user.total_karma_user.karma or 0

    def get_rank(self, obj):
        rank = (
            TotalKarma.objects.filter(user__total_karma_user__isnull=False)
            .annotate(rank=F("user__total_karma_user__karma"))
            .order_by("-rank")
            .values_list("rank", flat=True)
        )

        ranks = {karma: i + 1 for i, karma in enumerate(rank)}
        return ranks.get(obj.user.total_karma_user.karma, None)

    def get_level(self, obj):
        user_level_link = UserLvlLink.objects.filter(user=obj.user).first()
        if user_level_link:
            return user_level_link.level.name
        return None


class ListAllDistrictsSerializer(serializers.ModelSerializer):
    level = serializers.SerializerMethodField()
    lead = serializers.SerializerMethodField()
    lead_number = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ("title", "code", "level", "lead", "lead_number")

    def get_level(self, obj):
        college = College.objects.filter(org=obj).first()
        return college.level if college else None

    def get_lead(self, obj):
        user_org_link = obj.user_organization_link_org_id.filter(
            org__title=obj.title,
            user__user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value,
        ).first()
        return user_org_link.user.fullname if user_org_link else None

    def get_lead_number(self, obj):
        user_org_link = obj.user_organization_link_org_id.filter(
            org__title=obj.title,
            user__user_role_link_user__role__title=RoleType.CAMPUS_LEAD.value,
        ).first()
        return user_org_link.user.mobile if user_org_link else None
