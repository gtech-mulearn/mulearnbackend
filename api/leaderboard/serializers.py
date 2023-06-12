from django.db.models import Sum
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.organization import Organization
from db.task import TotalKarma
from db.user import UserRoleLink


# serializers.py

class StudentLeaderboardSerializer(serializers.ModelSerializer):
    totalKarma = serializers.IntegerField(source="karma")
    fullName = serializers.ReadOnlyField(source="user.fullname")
    institution = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ["fullName", "totalKarma", "institution"]

    def get_institution(self, obj):
        try:
            user_organization = obj.user.user_organization_link_user_id.first().org
            return user_organization.code if user_organization else None
        except Exception as e:
            return None


class StudentMonthlySerializer(serializers.ModelSerializer):
    code = serializers.SerializerMethodField()
    full_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = UserRoleLink
        fields = ['code', 'full_name', 'total_karma']

    def get_code(self, obj):
        user_organization_link = obj.user.user_organization_link_user_id.filter(org__org_type='College').first()
        return user_organization_link.org.code if user_organization_link else None


class CollegeLeaderboardSerializer(serializers.ModelSerializer):
    totalKarma = serializers.SerializerMethodField()
    institution = serializers.CharField(source='title')

    class Meta:
        model = Organization
        fields = ["code", "institution", "totalKarma"]

    def get_totalKarma(self, obj):
        try:
            total_karma = obj.user_organization_link_org_id.aggregate(total_karma=Sum('user__total_karma_user__karma'))[
                'total_karma']
            return total_karma if total_karma is not None else 0
        except Exception as e:
            return 0


class CollegeMonthlyLeaderboardSerializer(ModelSerializer):
    institution = serializers.CharField(source="title")
    totalKarma = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["code", "institution", "totalKarma"]

    def get_totalKarma(self, obj):
        total_karma = \
            obj.user_organization_link_org_id.aggregate(total_karma=Sum('user__karma_activity_log_created_by__karma'))[
                'total_karma']

        return total_karma or 0
