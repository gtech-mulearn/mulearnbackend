from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from db.organization import UserOrganizationLink, College
from db.task import KarmaActivityLog
from db.user import User
from utils.types import OrganizationType
from utils.types import RoleType
from utils.utils import DateTimeUtils


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
            campus_lead = campus_lead.fullname

        enabler = User.objects.filter(
            user_organization_link_user__org=obj.org,
            user_organization_link_user__org__org_type=OrganizationType.COLLEGE.value,
            user_role_link_user__role__title=RoleType.LEAD_ENABLER.value,
        ).first()
        if enabler:
            enabler = enabler.fullname

        return {'campus_lead': campus_lead, 'enabler': enabler}

    def get_campus_level(self, obj):
        campus = College.objects.filter(org=obj.org).first()
        if campus:
            return campus.level

        return None

    def get_total_members(self, obj):
        return obj.org.user_organization_link_org.count()

    def get_active_members(self, obj):

        last_month = DateTimeUtils.get_current_utc_time() - timedelta(weeks=26)  # 6months
        return obj.org.user_organization_link_org.filter(
            verified=True,
            user__wallet_user__isnull=False,
            user__wallet_user__karma_last_update_at__gte=last_month,
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
            UserOrganizationLink.objects.filter(org__org_type=OrganizationType.COLLEGE.value)
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
    fullname = serializers.SerializerMethodField()
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
    is_alumni = serializers.CharField()

    class Meta:
        fields = ("user_id", "email", "mobile", "fullname", "karma", "muid", "rank", "level", "join_date", "is_alumni",
                  "last_karma_update_at")

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

        for date in date_range:
            karma_logs = (
                KarmaActivityLog.objects.filter(
                    user__user_organization_link_user__org=instance.org,
                    created_at__date=date,
                ).aggregate(
                    karma=Sum("karma"),
                )
            )
            response[str(date)] = karma_logs.get("karma", 0)

        return response


class ChangeStudentTypeSerializer(serializers.Serializer):
    is_alumni = serializers.BooleanField(default=False)

    class Meta:
        model = UserOrganizationLink
        fields = ("is_alumni",)

    def update(self, instance, validated_data):
        instance.is_alumni = validated_data.get('is_alumni')
        instance.save()

        return instance


class ListAluminiSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    fullname = serializers.SerializerMethodField()
    muid = serializers.CharField()
    karma = serializers.IntegerField()
    rank = serializers.SerializerMethodField()
    level = serializers.CharField()
    join_date = serializers.CharField()

    class Meta:
        fields = ("user_id", "fullname", "karma", "muid", "rank", "level", "join_date")
