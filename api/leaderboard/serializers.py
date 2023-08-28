from django.db.models import Sum
from rest_framework import serializers

from db.organization import Organization
from db.task import TotalKarma


class StudentLeaderboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.IntegerField(source="karma")
    full_name = serializers.ReadOnlyField(source="user.fullname")
    institution = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ["full_name", "total_karma", "institution"]

    def get_institution(self, obj):
        try:
            user_organization = obj.user.user_organization_link_user_id.first().org
            return user_organization.code if user_organization else None
        except Exception as e:
            return None


class StudentMonthlySerializer(serializers.Serializer):
    id = serializers.CharField(source='user__id')
    full_name = serializers.SerializerMethodField()
    total_karma = serializers.IntegerField()

    def get_full_name(self, obj):
        return f"{obj['user__first_name']} {obj['user__last_name']}"


class CollegeLeaderboardSerializer(serializers.ModelSerializer):
    total_karma = serializers.SerializerMethodField()
    institution = serializers.CharField(source='title')

    class Meta:
        model = Organization
        fields = ["code", "institution", "total_karma"]

    def get_total_karma(self, obj):
        try:
            total_karma = obj.user_organization_link_org_id.aggregate(total_karma=Sum('user__total_karma_user__karma'))[
                'total_karma']
            return total_karma if total_karma is not None else 0
        except Exception as e:
            return 0


class CollegeMonthlyLeaderboardSerializer(serializers.ModelSerializer):
    institution = serializers.CharField(source="title")
    total_karma = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["code", "institution", "total_karma"]

    def get_total_karma(self, obj):
        try:
            total_karma = obj.user_organization_link_org_id.aggregate(total_karma=Sum('user__total_karma_user__karma'))[
                'total_karma']
            return total_karma if total_karma is not None else 0
        except Exception as e:
            return 0