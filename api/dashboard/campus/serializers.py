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
        return obj.org.user_organization_link_org_id.count()

    def get_active_members(self, obj):
        last_month = DateTimeUtils.get_current_utc_time(
        ) - timedelta(days=30)

        return obj.org.user_organization_link_org_id.filter(
            verified=True,
            user__active=True,
            user__total_karma_user__isnull=False,
            user__total_karma_user__created_at__gte=last_month,
        ).count()

    def get_total_karma(self, obj):
        return obj.org.user_organization_link_org_id.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            verified=True,
            user__total_karma_user__isnull=False,
        ).aggregate(total_karma=Sum(
            "user__total_karma_user__karma"))["total_karma"] or 0

    def get_rank(self, obj):
        org_karma_dict = (
            UserOrganizationLink.objects.all()
            .values("org")
            .annotate(total_karma=Sum("user__total_karma_user__karma"))
        )

        rank_dict = {
            data["org"]: data["total_karma"]
            if data["total_karma"] is not None
            else 0
            for data in org_karma_dict
        }

        sorted_rank_dict = dict(
            sorted(rank_dict.items(), key=lambda x: x[1], reverse=True)
        )

        if obj.org.id in sorted_rank_dict:
            keys_list = list(sorted_rank_dict.keys())
            position = keys_list.index(obj.org.id)
            return position + 1


# class CampusStudentInEachLevelSerializer(serializers.ModelSerializer):
#     # levels = serializers.SerializerMethodField()
#
#     class Meta:
#         model = UserOrganizationLink
#         fields = []
#
#     def to_representation(self, instance):
#         level_with_student_count = Level.objects.annotate(
#             students=Count('user_lvl_link_level__user', filter=Q(
#                 user_lvl_link_level__user__user_organization_link_user_id__org=instance.org)
#                            )).values(level=F('level_order'), students=F('students'))
#         print(level_with_student_count)
#         return level_with_student_count
#
#     def to_representation(self, instance):
#         return [{'students': 1, 'level': 5}, {'students': 1, 'level': 5}]


class CampusStudentDetailsSerializer(serializers.ModelSerializer):
    fullname = serializers.ReadOnlyField(source="user.fullname")
    muid = serializers.ReadOnlyField(source="user.mu_id")
    karma = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ("fullname",
                  "karma",
                  "muid",
                  "rank",
                  "level",
                  "created_at"
                  )

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
        user_level_link = UserLvlLink.objects.filter(
            user=obj.user).first()
        if user_level_link:
            return user_level_link.level.name
        return None


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
                user__user_organization_link_user_id__org=instance.org,
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
