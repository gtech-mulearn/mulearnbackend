from datetime import timedelta

from django.db.models import Sum, Count, Q, Case, When, IntegerField
from rest_framework import serializers

from db.organization import UserOrganizationLink, District, Organization
from db.task import KarmaActivityLog, Level
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
    karma = serializers.SerializerMethodField()

    def get_rank(self, district):
        keys_list = list(self.context.get("ranks").keys())
        position = keys_list.index(district.id)
        return position + 1

    def get_karma(self, district):
        return self.context.get("ranks")[district.id]

    class Meta:
        model = District
        fields = ["district", "id", "rank", "karma"]


class ZonalStudentLevelStatusSerializer(serializers.ModelSerializer):
    college_name = serializers.CharField(source="title")
    college_code = serializers.CharField(source="code")
    level = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["college_name", "college_code", "level"]

    def get_level(self, obj):
        return Level.objects.annotate(
            students_count=Count(
                Case(
                    When(
                        Q(
                            user_lvl_link_level__user__user_organization_link_user_id__org=obj.user_organization_link_org_id.first().org,
                        ),
                        then=1,
                    ),
                    default=None,
                    output_field=IntegerField(),
                )
            )
        ).values("level_order", "students_count")


class ZonalStudentDetailsSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    fullname = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()

    class Meta:
        fields = ["user_id", "fullname", "karma", "muid", "level", "rank"]

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

    def get_fullname(self, obj):
        return obj.fullname


class ZonalCollegeDetailsSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    code = serializers.CharField()
    level = serializers.CharField()
    lead = serializers.SerializerMethodField()
    lead_number = serializers.SerializerMethodField()

    def get_lead(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].fullname if college_lead else None

    def get_lead_number(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].mobile if college_lead else None

    class Meta:
        fields = ["id", "title", "code", "level", "lead", "lead_number"]
