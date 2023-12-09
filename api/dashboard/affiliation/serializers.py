import uuid

from rest_framework import serializers

from db.organization import OrgAffiliation
from utils.utils import DateTimeUtils


class AffiliationListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")
    organization_count = serializers.SerializerMethodField()

    class Meta:
        model = OrgAffiliation
        fields = ['id', 'title', 'organization_count', 'created_by', 'updated_by', 'updated_at', 'created_at']

    def get_organization_count(self, obj):
        return obj.organization_affiliation.count()


class AffiliationCUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAffiliation
        fields = ['title']

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
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()

        return instance
