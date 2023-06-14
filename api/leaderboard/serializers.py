from django.db.models import Sum
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.organization import Organization
from db.task import TotalKarma


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


class StudentMonthlySerializer(serializers.Serializer):
    id = serializers.CharField(source='user__id')
    fullName = serializers.SerializerMethodField()
    totalKarma = serializers.IntegerField()

    def get_fullName(self, obj):
        return f"{obj['user__first_name']} {obj['user__last_name']}"


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
        total_karma = obj.totalKarma
        return total_karma or 0
