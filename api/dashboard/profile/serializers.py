from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from db.task import KarmaActivityLog


class UserLogSerializer(ModelSerializer):
    taskName = serializers.ReadOnlyField(source='task.title')
    karmaPoint = serializers.CharField(source='karma')
    createdDate = serializers.CharField(source='created_at')
    class Meta:
        model = KarmaActivityLog
        fields = ["taskName", "karmaPoint", "createdDate"]

