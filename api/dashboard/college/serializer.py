from datetime import timedelta

from django.db.models import Sum
from rest_framework import serializers
from db.organization import College, Organization
from db.learning_circle import LearningCircle
from db.organization import College, UserOrganizationLink
from db.task import KarmaActivityLog
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils


class CollegeListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")
    number_of_students = serializers.SerializerMethodField()
    total_karma = serializers.SerializerMethodField()
    no_of_alumni = serializers.SerializerMethodField()
    no_of_lc = serializers.SerializerMethodField()
    lead_name = serializers.CharField(source="lead.fullname", default=None)
    lead_contact = serializers.CharField(source="lead.mobile", default=None)

    class Meta:
        model = Organization
        fields = [
            "id",
            "title",
            "code",
            "org_type",
            "affiliation",
            "district",
            "updated_by",
            "created_by",
            "updated_at",
            "created_at",
            "number_of_students",
            "no_of_alumni",
            "no_of_lc",
            "total_karma",
            "lead_name",
            "lead_contact",
        ]

    def get_no_of_alumni(self, obj):
        return obj.user_organization_link_org.filter(
            org__org_type=OrganizationType.COLLEGE.value,
            user__user_role_link_user__role__title=RoleType.STUDENT.value,
            is_alumni=True,
            verified=True,
        ).count()

    def get_no_of_lc(self, obj):
        learning_circle_count = LearningCircle.objects.filter(
            org=obj
        ).count()
        no_of_lc_increased = LearningCircle.objects.filter(
            org=obj,
            created_at__gte=DateTimeUtils.get_current_utc_time() - timedelta(days=30),
        ).count()
        return {
            "lc_count": learning_circle_count,
            "no_of_lc_increased": no_of_lc_increased,
        }

    def get_number_of_students(self, obj):
        return obj.user_organization_link_org.filter(
            user__user_role_link_user__role__title=RoleType.STUDENT.value
        ).count()

    def get_total_karma(self, obj):
        return (
            obj.user_organization_link_org.filter(
                org__org_type=OrganizationType.COLLEGE.value,
                verified=True,
                user__wallet_user__isnull=False,
            ).aggregate(total_karma=Sum("user__wallet_user__karma"))["total_karma"]
            or 0
        )


class CollegeCreateDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = [
            "level",
            "org",
            "updated_by",
            "created_by",
        ]


class CollegeEditSerializer(serializers.ModelSerializer):
    class Meta:
        model = College
        fields = ["level", "updated_by"]
