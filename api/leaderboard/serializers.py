from django.db.models import Sum
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from db.organization import UserOrganizationLink
from db.task import TotalKarma
from db.user import UserRoleLink


class StudentLeaderboardSerializer(ModelSerializer):
    totalKarma = serializers.IntegerField(source="karma")
    fullName = serializers.ReadOnlyField(source="user.fullname")
    institution = serializers.SerializerMethodField()

    class Meta:
        model = TotalKarma
        fields = ["fullName", "totalKarma", "institution"]

    def get_institution(self, obj):
        try:
            # no use .first()
            user_organization = obj.user.user_organization_link_user_id.filter(org__org_type__in=["College", "School"]).first()
            # user_organization = obj.user.user_organization_link_user_id.first()
            return user_organization.org.code if user_organization.org else None
        except:
            return None


class StudentMonthlySerializer(ModelSerializer):
    code = serializers.SerializerMethodField()
    fullName = serializers.ReadOnlyField(source="user.fullname")
    totalKarma = serializers.SerializerMethodField()

    class Meta:
        model = UserRoleLink
        fields = ["code", "fullName", "totalKarma"]

    def get_totalKarma(self, obj):

        start_date = self.context.get('start_date')
        end_date = self.context.get('end_date')

        try:
            monthly_karma = obj.user.karma_activity_log_created_by.filter(
                created_at__range=(start_date, end_date)).aggregate(Sum('karma')).get(
                'karma__sum') if obj.user.karma_activity_log_created_by.filter(
                created_at__range=(start_date, end_date)).aggregate(Sum('karma')).get('karma__sum') else 0
        except:
            monthly_karma = 0
        return monthly_karma

    def get_code(self, obj):

        try:
            user_organization_link = obj.user.user_organization_link_user_id.all().first()
        except:
            user_organization_link = None
        return user_organization_link.org.code if user_organization_link else None


class CollegeLeaderboardSerializer(ModelSerializer):
    code = serializers.ReadOnlyField(source='org.code')
    totalKarma = serializers.SerializerMethodField()
    institution = serializers.ReadOnlyField(source='org.title')

    class Meta:
        model = UserOrganizationLink
        fields = ["code", "totalKarma", "institution"]

    def get_totalKarma(self, obj):

        print(obj.org.updated_by)
        # try:
        #     user_organization_link = obj.user.user_organization_link_user_id.all().first()
        # except:
        #     user_organization_link = None
        # return user_organization_link.org.code if user_organization_link else None
        try:
            monthly_karma = obj.user.karma_activity_log_created_by.aggregate(Sum('karma')).get('karma__sum')
        except:
            monthly_karma = 0
        return monthly_karma
