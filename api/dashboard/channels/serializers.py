from rest_framework import serializers
from db.task import Channel
from django.utils import timezone
from utils.utils import DateTimeUtils
import uuid
class ChannelReadSerializer(serializers.ModelSerializer):

    name = serializers.ReadOnlyField()
    discord_id = serializers.ReadOnlyField()
    channel_id = serializers.ReadOnlyField(source='id')
    updated_at = serializers.ReadOnlyField()
    created_at = serializers.ReadOnlyField()

    class Meta:
        model = Channel
        fields = [
            "name",
            "channel_id",
            "discord_id",
            "created_at",
            "updated_at"
        ]

class ChannelCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = [
            "name",
            "discord_id"
        ]
    
    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['id'] = uuid.uuid4()
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        return Channel.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        instance.name = validated_data.get('name', instance.name)
        instance.discord_id = validated_data.get('discord_id', instance.name)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance