from rest_framework import serializers
from portal.models import Portal
from uuid import uuid4


class PortalSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        if not (attrs["title"] and len(attrs["title"]) < 100):
            raise serializers.ValidationError("No title")
        return attrs

    def create(self, validated_data):
        obj = Portal.objects.create(
            **validated_data, id=uuid4(), access_id=uuid4())
        return obj

    class Meta:
        model = Portal
        fields = ["title", "link"]
