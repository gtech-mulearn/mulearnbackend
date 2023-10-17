from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from db.organization import UserOrganizationLink
from db.task import KarmaActivityLog
from db.user import User
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
            user__wallet_user__isnull=False,
            user__wallet_user__created_at__gte=last_month,
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
            UserOrganizationLink.objects.all()
            .values("org")
            .annotate(total_karma=Sum("user__wallet_user__karma"))
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


class StudentLeaderboardSerializer(serializers.ModelSerializer):
    institution = serializers.SerializerMethodField()
    total_karma = serializers.IntegerField(source="wallet_user.karma", default=0)
    full_name = serializers.CharField(source="fullname")

    def get_institution(self, user):
        return user.colleges[0].org.title if user.colleges else None

    class Meta:
        model = User
        fields = ["full_name", "total_karma", "institution"]
