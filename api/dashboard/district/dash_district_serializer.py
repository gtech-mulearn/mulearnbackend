from datetime import timedelta

from django.db.models import Count, Sum
from rest_framework import serializers

from db.organization import UserOrganizationLink, Organization
from db.task import KarmaActivityLog, Level
from db.user import User
from utils.types import OrganizationType, RoleType
from utils.utils import DateTimeUtils

# How long the zone / district karma ranking is cached (one fixed key each).
RANKING_TTL = 60 * 15


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
        # The ranking is a GROUP BY over every college membership on the
        # platform. Its key space is one fixed key (all districts at once), so
        # it is cached for RANKING_TTL and may lag karma by up to that long.
        from django.core.cache import cache

        try:
            ranking = cache.get("dashboard:district_karma_ranking")
        except Exception:
            ranking = None
        if ranking is None:
            org_karma_dict = (
                UserOrganizationLink.objects.filter(
                    org__org_type=OrganizationType.COLLEGE.value)
                .values("org__district")
                .annotate(total_karma=Sum("user__wallet_user__karma"))
            ).order_by("-total_karma", "org__created_at")

            rank_dict = {
                data["org__district"]: data["total_karma"]
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
                cache.set("dashboard:district_karma_ranking", ranking, RANKING_TTL)
            except Exception:
                pass

        if obj.org.district.id in ranking:
            return ranking.index(obj.org.district.id) + 1

    def get_district_lead(self, obj):
        user_org_link = UserOrganizationLink.objects.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            org__district=obj.org.district,
            user__user_role_link_user__role__title=RoleType.DISTRICT_CAMPUS_LEAD.value,
        ).first()
        return user_org_link.user.full_name if user_org_link else None

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

    def _counts_by_level(self):
        # One grouped query for all levels. With many=True this serializer
        # instance is reused for every level, so the result is cached on it;
        # it used to be one COUNT(DISTINCT) query per level.
        if getattr(self, "_level_counts", None) is None:
            district = self.context.get("district")
            self._level_counts = dict(
                User.objects.filter(
                    user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
                    user_organization_link_user__org__district=district,
                    user_lvl_link_user__level__isnull=False,
                )
                .values_list("user_lvl_link_user__level_id")
                .annotate(students=Count("id", distinct=True))
            )
        return self._level_counts

    def get_students_count(self, obj):
        return self._counts_by_level().get(obj.id, 0)


class DistrictStudentDetailsSerializer(serializers.Serializer):
    full_name = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()

    class Meta:
        fields = (
            "full_name",
            "karma",
            "muid",
            "rank",
            "level",
        )

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

    def get_full_name(self, obj):
        return obj.full_name


class DistrictCollegeDetailsSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    code = serializers.CharField()
    level = serializers.CharField()
    lead = serializers.SerializerMethodField()

    class Meta:
        fields = (
            'id',
            'title',
            'level',
            'code',
            'lead',
        )

    def get_lead(self, obj):
        leads = self.context.get("leads")
        college_lead = [lead for lead in leads if lead.college == obj["id"]]
        return college_lead[0].full_name if college_lead else None
