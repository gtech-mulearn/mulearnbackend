import uuid

from rest_framework import serializers

from db.task import Channel

class ChannelCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Channel
        fields = ['name', 'discord_id', 'id']
        read_only_fields = ['id']

    def create(self, validated_data):
        user_id = self.context.get("user_id")

        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        
        return Channel.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        
        instance.name = validated_data.get("name", instance.name)
        instance.discord_id = validated_data.get("discord_id", instance.discord_id)
        instance.updated_by_id = user_id
        instance.save()
         
        return instance