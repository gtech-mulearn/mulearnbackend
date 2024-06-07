from rest_framework import serializers

from db.user import User

class LaunchpadLeaderBoardSerializer(serializers.ModelSerializer):
    rank = serializers.IntegerField()
    karma = serializers.IntegerField()
    org = serializers.CharField()
    district_name = serializers.CharField()
    state = serializers.CharField()

    class Meta:
        model = User
        fields = ("rank", "full_name", "karma", "org", "district_name", "state")
