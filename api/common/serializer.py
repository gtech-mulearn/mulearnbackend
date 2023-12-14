from rest_framework import serializers

from db.user import User


class StudentInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
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
    first_name = serializers.CharField()
    last_name = serializers.CharField()
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
    fullname = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'fullname',
            "karma",
            "interest_groups",
            "organizations",
        )

    def get_fullname(self, obj):
        return obj.fullname

    def get_organizations(self, obj):
        return obj.user_organization_link_user.all().values_list("org__title", flat=True)

    def get_interest_groups(self, obj):
        return obj.user_ig_link_user.all().values_list("ig__name", flat=True)
