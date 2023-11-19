import uuid
from utils.utils import DateTimeUtils
from rest_framework import serializers
from db.organization import College, Organization
from utils.types import RoleType, OrganizationType
from django.db.models import Sum


class CollegeListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")
    org = serializers.CharField(source="org.title")
    number_of_students = serializers.SerializerMethodField()
    lead_name = serializers.CharField(source="lead.fullname", default=None)
    lead_contact = serializers.CharField(source="lead.mobile", default=None)
    total_karma = serializers.SerializerMethodField()

    class Meta:
        model = College
        fields = [
            "id",
            "level",
            "org",
            "updated_by",
            "created_by",
            "updated_at",
            "created_at",
            "number_of_students",
            "lead_name",
            "lead_contact",
            "total_karma",
        ]

    def get_number_of_students(self, obj):
        return obj.org.user_organization_link_org.filter(
            user__user_role_link_user__role__title=RoleType.STUDENT.value
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
