from rest_framework import serializers
from db.task import KarmaActivityLog
from db.user import User

class KarmaActivityLogSerializer(serializers.ModelSerializer):
    fullname = serializers.CharField(source = 'user.fullname')
    task_name = serializers.CharField(source = 'task.title')
    status = serializers.SerializerMethodField()
    discordlink = serializers.CharField(source = 'task.discord_link')
    class Meta:
        model = KarmaActivityLog
        fields = ['id', 'fullname', 'task_name', 'status', 'discordlink'] 

    def get_status(self,obj):
        if obj.peer_approved == True and obj.appraiser_approved == True:
            return "Karma Awarded"
        elif obj.peer_approved== True:
            return "Peer Approved"
        elif obj.appraiser_approved == True:
            return "Appraiser Approved"
        else:
            return "Pending"


