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


class LaunchpadParticipantsSerializer(serializers.ModelSerializer):
    org = serializers.CharField()
    district_name = serializers.CharField()
    state = serializers.CharField()
    level = serializers.CharField()

    class Meta:
        model = User
        fields = ("full_name", "level", "org", "district_name", "state")


class LaunchpadDetailsCountSerializer(serializers.ModelSerializer):
    total_participants = serializers.SerializerMethodField()
    level_1 = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = [
            'total_participants',
            'level_1'
        ]

    # def get_total_participants(self, obj):
    #     return len(obj)
    #
    # def get_level_1(self,obj):
    #     for data in obj:
    #
    #     return 1