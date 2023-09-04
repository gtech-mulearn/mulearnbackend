from datetime import timedelta

from django.db.models import Case, F, IntegerField, Sum, Value, When, Count, Q
from rest_framework import serializers

from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog, Level, TotalKarma, UserLvlLink
from utils.types import OrganizationType
from utils.utils import DateTimeUtils


class CampusDetailsSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="org.title")
    campus_code = serializers.ReadOnlyField(source="org.code")
    campus_zone = serializers.ReadOnlyField(source="org.district.zone.name")
    campus_lead = serializers.ReadOnlyField(source="user.fullname")
    total_karma = serializers.SerializerMethodField()
    total_members = serializers.SerializerMethodField()
    active_members = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = [
            "college_name",
            "campus_lead",
            "campus_code",
            "campus_zone",
            "total_karma",
            "total_members",
            "active_members",
            "rank",
        ]

    def get_total_members(self, obj):
        return obj.org.user_organization_link_org.count()

    def get_active_members(self, obj):
        last_month = DateTimeUtils.get_current_utc_time() - timedelta(days=30)
        return obj.org.user_organization_link_org.filter(
            verified=True,
            user__active=True,
            user__total_karma_user__isnull=False,
            user__total_karma_user__created_at__gte=last_month,
        ).count()

    def get_total_karma(self, obj):
        return (
            obj.org.user_organization_link_org.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
                user__total_karma_user__isnull=False,
            ).aggregate(total_karma=Sum("user__total_karma_user__karma"))["total_karma"]
            or 0
        )

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.all()
            .values("org")
            .annotate(total_karma=Sum("user__total_karma_user__karma"))
        )

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
    fullname = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    join_date = serializers.CharField()

    class Meta:
        fields = ("user_id", "fullname", "karma", "muid", "rank", "level", "join_date")

    def get_rank(self, obj):
        ranks = self.context.get("ranks")
        return ranks.get(obj.id, None)

    def get_fullname(self, obj):
        return obj.fullname


class WeeklyKarmaSerializer(serializers.ModelSerializer):
    college_name = serializers.ReadOnlyField(source="org.title")

    class Meta:
        model = UserOrganizationLink
        fields = ["college_name"]

    def to_representation(self, instance):
        response = super().to_representation(instance)

        today = DateTimeUtils.get_current_utc_time().date()
        date_range = [today - timedelta(days=i) for i in range(7)]

        karma_logs = (
            KarmaActivityLog.objects.filter(
                user__user_organization_link_user__org=instance.org,
                created_at__date__in=date_range,
            )
            .annotate(
                date_index=Case(
                    *[
                        When(created_at__date=date, then=Value(i))
                        for i, date in enumerate(date_range)
                    ],
                    output_field=IntegerField(),
                )
            )
            .values("date_index")
            .annotate(total_karma=Sum("karma"))
            .values_list("total_karma", flat=True)
        ) or []
        karma_data = {
            i + 1: karma_logs[i] if i < len(karma_logs) else 0
            for i in range(len(date_range))
        }
        response["karma"] = karma_data

        return response
