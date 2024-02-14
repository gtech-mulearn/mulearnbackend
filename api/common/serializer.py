from rest_framework import serializers

from db.user import User
from db.organization import (
    Country,
    Department,
    District,
    Organization,
    State,
    UserOrganizationLink,
    Zone,
)

class StudentInfoSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    muid = serializers.CharField()
    circle_name = serializers.CharField()
    circle_ig = serializers.CharField()
    organisation = serializers.CharField()
    dwms_id = serializers.CharField(allow_null=True)
    karma_earned = serializers.IntegerField()


class CollegeInfoSerializer(serializers.Serializer):
    org_title = serializers.CharField()
    learning_circle_count = serializers.CharField()
    user_count = serializers.CharField()


class LearningCircleEnrollmentSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    muid = serializers.CharField()
    email = serializers.CharField()
    dwms_id = serializers.CharField(allow_null=True)
    circle_name = serializers.CharField()
    circle_ig = serializers.CharField()
    organisation = serializers.CharField()
    district = serializers.CharField(allow_null=True)
    karma_earned = serializers.IntegerField()


class UserLeaderboardSerializer(serializers.ModelSerializer):
    interest_groups = serializers.SerializerMethodField()
    organizations = serializers.SerializerMethodField()
    karma = serializers.IntegerField(source="wallet_user.karma")
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'full_name',
            "karma",
            "interest_groups",
            "organizations",
        )

    def get_full_name(self, obj):
        return obj.full_name

    def get_organizations(self, obj):
        return obj.user_organization_link_user.all().values_list("org__title", flat=True)

    def get_interest_groups(self, obj):
        return obj.user_ig_link_user.all().values_list("ig__name", flat=True)



class OrgSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ["id", "title"]

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name"]

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name"]
class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name"]