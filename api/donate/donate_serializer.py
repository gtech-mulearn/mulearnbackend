import uuid

from rest_framework import serializers
from django.conf import settings

from db.donor import Donor
from utils.utils import DateTimeUtils


class DonorSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(allow_null=True, allow_blank=True, default='INR')
    company = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    phone_number = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    pan_number = serializers.CharField(allow_null=True, allow_blank=True, required=False)

    class Meta:
        model = Donor
        exclude = ['created_by', 'created_at', 'id', 'payment_id', 'payment_method']

    def create(self, validated_data):
        validated_data["created_by_id"] = settings.SYSTEM_ADMIN_ID
        validated_data["id"] = uuid.uuid4()
        return Donor.objects.create(**validated_data)


class SubscriptionSerializer(serializers.Serializer):
    """Serializer for subscription creation requests"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(default='INR')
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    pan_number = serializers.CharField(max_length=10, required=False, allow_blank=True)
    company = serializers.CharField(max_length=255, required=False, allow_blank=True)
    donation_type = serializers.ChoiceField(choices=['monthly', 'yearly'])
    is_organisation = serializers.BooleanField(default=False)
