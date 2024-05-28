from rest_framework import serializers

from db.user import User

class LaunchpadLeaderBoardSerializer(serializers.ModelSerializer):
    karma = serializers.IntegerField()
    org = serializers.CharField()
    district = serializers.CharField()
    state = serializers.CharField()

    class Meta:
        model = User
        fields = "__all__"
