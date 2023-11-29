from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers

from db.learning_circle import LearningCircle
from db.organization import College
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils


class CollegeListSerializer(serializers.ModelSerializer):
    org = serializers.CharField(source="org.title")
    number_of_members = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    no_of_lc = serializers.SerializerMethodField()
    no_of_alumni = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = [
            "id",
            # "level",
            "org",
            "number_of_members",
            "total_karma",
            "no_of_lc",
            "no_of_alumni",
        ]

    def get_no_of_alumni(self, obj):
        return obj.org.user_organization_link_org.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            user__user_role_link_user__role__title=RoleType.STUDENT.value,
            is_alumni=True,
            verified=True,
        ).count()

    def get_no_of_lc(self, obj):
        learning_circle_count = LearningCircle.objects.filter(org=obj.org).count()
        LearningCircle.objects.filter(org=obj.org,
                                      created_at__lte=DateTimeUtils.get_current_utc_time() - timedelta(days=30)).count()
        return {'lc_count': learning_circle_count, 'no_of_lc_increased': 1}

    def get_number_of_members(self, obj):
        member_count = obj.org.user_organization_link_org.all().count()

        no_of_members_increased = obj.org.user_organization_link_org.filter(
            created_at__lte=DateTimeUtils.get_current_utc_time() - timedelta(days=30)
        ).count()
        return {'member_count': member_count, 'no_of_members_increased': no_of_members_increased}

    def get_total_karma(self, obj):
        total_karma_gained = (
                obj.org.user_organization_link_org.filter(
                    org__org_type=OrganizationType.COLLEGE.value,
                    is_alumni=False,
                    verified=True,
                    user__wallet_user__isnull=False,
                ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]
                or 0
        )
        total_karma_increased = (
                obj.org.user_organization_link_org.filter(
                    org__org_type=OrganizationType.COLLEGE.value,
                    is_alumni=False,
                    verified=True,
                    user__wallet_user__isnull=False,
                    user__wallet_user__created_at__gt=DateTimeUtils.get_current_utc_time() - timedelta(days=30),
                ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]
                or 0
        )
        increased_percentage = total_karma_increased * 100 / 100
        return {'total_karma_gained': total_karma_gained, 'total_karma_increased': total_karma_increased,
                'increased_percentage': increased_percentage}
