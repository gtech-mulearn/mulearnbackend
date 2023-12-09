from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from db.organization import UserOrganizationLink, Organization
from db.task import KarmaActivityLog, Level
from db.user import User
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils


class DistrictDetailsSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source="org.district.name")
    zone = serializers.CharField(source="org.district.zone.name")
    rank = serializers.SerializerMethodField()
    district_lead = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = (
            "district",
            "zone",
            "rank",
            "district_lead",
            "karma",
            "total_members",
            "active_members",
        )

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
            .values("org__district")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
        ).order_by("-total_karma", "org__created_at")

        rank_dict = {
            data["org__district"]: data["total_karma"]
            if data["total_karma"] is not None
            else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.org.district.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.district.id)
            return position + 1

    def get_district_lead(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district=obj.org.district,
            user__user_role_link_user__role__title=RoleType.DISTRICT_CAMPUS_LEAD.value,
        ).first()
        return user_org_link.user.fullname if user_org_link else None

    def get_karma(self, obj):
        return UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district=obj.org.district
        ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]

    def get_total_members(self, obj):
        return UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district=obj.org.district
        ).count()

    def get_active_members(self, obj):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(
            day=1, month=start_date.month % 12 + 1
        ) - timedelta(days=1)

        return KarmaActivityLog.objects.filter(
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user__user_organization_link_user__org__district=obj.org.district,
            created_at__range=(start_date, end_date),
        ).count()


class DistrictTopThreeCampusSerializer(serializers.ModelSerializer):
    campus_code = serializers.CharField(source="code")
    rank = serializers.SerializerMethodField()
    karma = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["rank", "campus_code", "karma"]

    def get_rank(self, obj):
        keys_list = list(self.context.get("ranks").keys())
        position = keys_list.index(obj.id)
        return position + 1

    def get_karma(self, obj):
        return self.context.get("ranks")[obj.id]


class DistrictStudentLevelStatusSerializer(serializers.ModelSerializer):
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ["level_order", "students_count"]

    def get_students_count(self, obj):
        district = self.context.get("district")
        return (
            User.objects.filter(
                user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                user_organization_link_user__org__district=district,
                user_lvl_link_user__level=obj,
            )
            .distinct()
            .count()
        )


class DistrictStudentDetailsSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    fullname = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()

    class Meta:
        fields = (
            "user_id"
            "fullname",
            "karma",
            "muid",
            "rank",
            "level",
        )

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

    def get_fullname(self, obj):
        return obj.fullname


class DistrictCollegeDetailsSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    code = serializers.CharField()
    level = serializers.CharField()
    lead = serializers.SerializerMethodField()
    lead_number = serializers.SerializerMethodField()

    class Meta:
        fields = (
            'id'
            'title',
            'level',
            'code',
            'lead',
            'lead_number'
        )

    def get_lead(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].fullname if college_lead else None

    def get_lead_number(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].mobile if college_lead else None
