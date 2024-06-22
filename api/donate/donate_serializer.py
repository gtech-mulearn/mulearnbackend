import uuid

from rest_framework import serializers
from django.conf import settings

from db.donor import Donor
from utils.utils import DateTimeUtils


class DonorSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(allow_null=True, allow_blank=True, default='INR')

    class Meta:
        model = Donor
        exclude = ['created_by', 'created_at', 'id', 'payment_id', 'payment_method']

    def create(self, validated_data):
        validated_data["created_by_id"] = settings.SYSTEM_ADMIN_ID
        validated_data["id"] = uuid.uuid4()
        return Donor.objects.create(**validated_data)
