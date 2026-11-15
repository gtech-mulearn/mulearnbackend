from datetime import timedelta

from django.db.models import Count, Sum
from rest_framework import serializers

from db.organization import UserOrganizationLink, District
from db.task import KarmaActivityLog, Level
from db.user import User
from utils.types import OrganizationType
from utils.utils import DateTimeUtils

# How long the zone / district karma ranking is cached (one fixed key each).
RANKING_TTL = 60 * 15


class ZonalDetailsSerializer(serializers.ModelSerializer):
    zone = serializers.CharField(source="org.district.zone.name")
    rank = serializers.SerializerMethodField()
    zonal_lead = serializers.CharField(source="user.full_name")
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
        # The ranking is a GROUP BY over every college membership on the
        # platform. Its key space is one fixed key (all zones at once), so
        # it is cached for RANKING_TTL and may lag karma by up to that long.
        from django.core.cache import cache

        try:
            ranking = cache.get("dashboard:zone_karma_ranking")
        except Exception:
            ranking = None
        if ranking is None:
            org_karma_dict = (
                UserOrganizationLink.objects.filter(
                    org__org_type=OrganizationType.COLLEGE.value)
                .values("org__district__zone")
                .annotate(total_karma=Sum("user__wallet_user__karma"))
            ).order_by("-total_karma", "org__created_at")

            rank_dict = {
                data["org__district__zone"]: data["total_karma"]
                if data["total_karma"] is not None
                else 0
                for data in org_karma_dict
            }

            # Same order as before: by karma, highest first (stable sort keeps
            # the query's created_at tie order).
            ranking = [
                key for key, _ in sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
            ]
            try:
                cache.set("dashboard:zone_karma_ranking", ranking, RANKING_TTL)
            except Exception:
                pass

        if obj.org.district.zone.id in ranking:
            return ranking.index(obj.org.district.zone.id) + 1

    def get_karma(self, obj):
        return UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district__zone=obj.org.district.zone,
        ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]

    def get_total_members(self, obj):
        return UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district__zone=obj.org.district.zone,
        ).count()

    def get_active_members(self, obj):
        today = DateTimeUtils.get_current_utc_time()
        start_date = today.replace(day=1)
        end_date = start_date.replace(
            day=1, month=(start_date.month % 12) + 1
        ) - timedelta(days=1)

        return KarmaActivityLog.objects.filter(
            user__user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user__user_organization_link_user__org__district__zone=obj.org.district.zone,
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
        fields = ["district", "rank", "karma"]


class ZonalStudentLevelStatusSerializer(serializers.ModelSerializer):
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Level
        fields = ["level_order", "students_count"]

    def _counts_by_level(self):
        # One grouped query for all levels. With many=True this serializer
        # instance is reused for every level, so the result is cached on it;
        # it used to be one COUNT(DISTINCT) query per level.
        if getattr(self, "_level_counts", None) is None:
            zone = self.context.get("zone")
            self._level_counts = dict(
                User.objects.filter(
                    user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user_organization_link_user__org__district__zone=zone,
                    user_lvl_link_user__level__isnull=False,
                )
                .values_list("user_lvl_link_user__level_id")
                .annotate(students=Count("id", distinct=True))
            )
        return self._level_counts

    def get_students_count(self, obj):
        return self._counts_by_level().get(obj.id, 0)


class ZonalStudentDetailsSerializer(serializers.Serializer):
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()

    class Meta:
        fields = ["full_name", "karma", "muid", "level", "rank"]

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

    def get_full_name(self, obj):
        return obj.full_name


class ZonalCollegeDetailsSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    code = serializers.CharField()
    level = serializers.CharField()
    lead = serializers.SerializerMethodField()

    def get_lead(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].full_name if college_lead else None

    class Meta:
        fields = ["id", "title", "code", "level", "lead"]
