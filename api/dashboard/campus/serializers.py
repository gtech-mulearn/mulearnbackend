from rest_framework import serializers
from db.organization import UserOrganizationLink
from db.task import TotalKarma


class UserOrgSerializer(serializers.ModelSerializer):
    fullname = serializers.ReadOnlyField(source="user.fullname")
    email = serializers.ReadOnlyField(source="user.email")
    phone = serializers.ReadOnlyField(source="user.mobile")
    muid = serializers.ReadOnlyField(source="user.mu_id")
    karma = serializers.SerializerMethodField()
    # rank = serializers.SerializerMethodField()
    class Meta:
        model = TotalKarma
        fields = ["fullname", "email", "phone", "karma","muid"]

    def get_karma(self, obj):
        try:
            karma = obj.user.total_karma_user.karma
        except:
            karma = 0
        return karma

    # def get_rank(self, obj):
    #     queryset = UserOrganizationLink.objects.order_by(
    #         "-user__total_karma_user__karma")
    #     rank = list(queryset).index(obj)
    #     return rank


class CollegeSerializer(serializers.ModelSerializer):
    collegeName = serializers.ReadOnlyField(source="org.title")
    campusCode = serializers.ReadOnlyField(source="org.code")
    campusZone = serializers.ReadOnlyField(source="org.district.zone.name")
    campusLead = serializers.ReadOnlyField(source="user.fullname")
    totalKarma = serializers.SerializerMethodField()
    totalMembers = serializers.SerializerMethodField()
    activeMembers = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()

    class Meta:
        model = UserOrganizationLink
        fields = ["collegeName", "campusLead", "campusCode",
                  "campusZone", "totalKarma", "totalMembers", "activeMembers", "rank"]

    def get_totalKarma(self, obj):
        karma = 0
        for user_org_link in obj.org.user_organization_link_org_id.filter(verified=True):
            karma += user_org_link.user.total_karma_user.karma
        return karma

    def get_totalMembers(self, obj):
        return obj.org.user_organization_link_org_id.count()

    def get_activeMembers(self, obj):
        return obj.org.user_organization_link_org_id.filter(verified=True, user__active=True).count()

    def get_rank(self, obj):
        return 1
