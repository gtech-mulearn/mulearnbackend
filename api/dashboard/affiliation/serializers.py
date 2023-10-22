import uuid

from rest_framework import serializers

from db.organization import OrgAffiliation

class AffiliationCRUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAffiliation
        fields = ['name', 'discord_id', 'id']
        read_only_fields = ['id']

    def create(self, validated_data):
        user_id = self.context.get("user_id")

        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        return OrgAffiliation.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        
        instance.title = validated_data.get("title", instance.title)
        instance.updated_by_id = user_id
        instance.save()
         
        return instance