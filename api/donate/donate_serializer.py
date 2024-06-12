import uuid

from rest_framework import serializers
from django.conf import settings

from db.donor import Donor
from utils.utils import DateTimeUtils


class DonorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Donor
        exclude = ['created_by', 'created_at', 'updated_by', 'updated_at', 'id']

    def create(self, validated_data):
        validated_data["created_by_id"] = settings.SYSTEM_ADMIN_ID
        validated_data["updated_by_id"] = settings.SYSTEM_ADMIN_ID
        validated_data["id"] = uuid.uuid4()
        return Donor.objects.create(**validated_data)
