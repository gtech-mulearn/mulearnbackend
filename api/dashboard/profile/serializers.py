from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from db.task import KarmaActivityLog, TotalKarma, UserIgLink


class UserLogSerializer(ModelSerializer):
    taskName = serializers.ReadOnlyField(source='task.title')
    karmaPoint = serializers.CharField(source='karma')
    createdDate = serializers.CharField(source='created_at')

    class Meta:
        model = KarmaActivityLog
        fields = ["taskName", "karmaPoint", "createdDate"]


class UserInterestGroupSerializer(ModelSerializer):
    interestGroup = serializers.ReadOnlyField(source='ig.name')
    class Meta:
        model = UserIgLink
        fields = ["interestGroup"]
