from rest_framework import serializers

from db.user import User

class LaunchpadLeaderBoardSerializer(serializers.ModelSerializer):
    karma = serializers.IntegerField()
    org = serializers.ReadOnlyField(source="user_organization_link_user.org.title")
    district_name = serializers.ReadOnlyField(source="user_organization_link_user.org.district.name")
    state = serializers.ReadOnlyField(source="user_organization_link_user.org.district.zone.state.name")

    class Meta:
        model = User
        fields = ("full_name", "karma", "org", "district_name", "state")
