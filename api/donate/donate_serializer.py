import uuid

from rest_framework import serializers
from django.conf import settings

from db.donor import Donor
from db.donation import Donation
from utils.utils import DateTimeUtils


class DonorSerializer(serializers.ModelSerializer):
    """Serializer for Donor model - personal info only"""
    company = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    phone_number = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    pan_number = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    address = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    is_organisation = serializers.BooleanField(default=False)

    class Meta:
        model = Donor
        exclude = ['created_by', 'created_at', 'id']

    def create(self, validated_data):
        validated_data["created_by_id"] = settings.SYSTEM_ADMIN_ID
        validated_data["id"] = uuid.uuid4()
        return Donor.objects.create(**validated_data)


class DonationSerializer(serializers.ModelSerializer):
    """Serializer for Donation model - payment tracking"""
    donation_type = serializers.ChoiceField(choices=['one-time', 'monthly', 'yearly'])
    
    class Meta:
        model = Donation
        exclude = ['id', 'created_at']

    def create(self, validated_data):
        validated_data["id"] = uuid.uuid4()
        return Donation.objects.create(**validated_data)


class SubscriptionSerializer(serializers.Serializer):
    """Serializer for subscription creation requests"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(default='INR')
    name = serializers.CharField(max_length=255)
    donation_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    pan_number = serializers.CharField(max_length=10, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(max_length=255, required=False, allow_blank=True)
    donation_type = serializers.ChoiceField(choices=['one-time', 'monthly', 'yearly'])
    is_organisation = serializers.BooleanField(default=False)


class OrderSerializer(serializers.Serializer):
    """Serializer for one-time order creation requests"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(default='INR')
    name = serializers.CharField(max_length=255)
    donation_name = serializers.CharField(max_length=100, required=False, allow_blank=True)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    pan_number = serializers.CharField(max_length=10, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    company = serializers.CharField(max_length=255, required=False, allow_blank=True)
    donation_type = serializers.ChoiceField(choices=['one-time', 'monthly', 'yearly'], default='one-time')
    is_organisation = serializers.BooleanField(default=False)

