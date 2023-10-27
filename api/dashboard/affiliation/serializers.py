from rest_framework import serializers
from db.organization import OrgAffiliation
import uuid

class AffiliationReadSerializer(serializers.ModelSerializer):

    title = serializers.ReadOnlyField()
    affiliation_id = serializers.ReadOnlyField(source='id')

    class Meta:
        model = OrgAffiliation
        fields = [
            "title",
            "affiliation_id"
        ]

class AffiliationCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAffiliation
        fields = [
            "title"
        ]
    
    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        validated_data['id'] = uuid.uuid4()
        return OrgAffiliation.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        instance.title = validated_data.get('title', instance.title)
        instance.updated_by_id = user_id

        instance.save()
        return instance