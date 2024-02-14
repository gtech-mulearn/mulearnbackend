from rest_framework import serializers
from db.task import KarmaActivityLog
from db.user import User


class KarmaActivityLogSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name')
    task_name = serializers.CharField(source='task.title')
    status = serializers.SerializerMethodField()
    discordlink = serializers.CharField(source='task.discord_link')

    class Meta:
        model = KarmaActivityLog
        fields = ['id', 'full_name', 'task_name', 'status', 'discordlink']

    def get_status(self, obj):
        if obj.peer_approved == True and obj.appraiser_approved == True:
            return "Karma Awarded"
        elif obj.peer_approved == True:
            return "Peer Approved"
        elif obj.appraiser_approved == True:
            return "Appraiser Approved"
        else:
            return "Pending"


class LeaderboardSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    count = serializers.IntegerField()
    muid = serializers.CharField(max_length=100)

    class Meta:
        model = KarmaActivityLog
        fields = ['name', 'count', 'muid']