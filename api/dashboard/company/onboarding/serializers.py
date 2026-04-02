import re

from rest_framework import serializers

from db.company import Company
from db.organization import District, Organization
from db.user import User
from utils.types import OrganizationType


PHONE_REGEX = re.compile(r"^\+?[0-9]{8,15}$")


class CompanySignupSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=75, required=True)
    poc_name = serializers.CharField(max_length=150, required=True)
    poc_email = serializers.EmailField(max_length=200, required=True)
    password = serializers.CharField(min_length=8, max_length=200, required=True, write_only=True)

    poc_phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    website_link = serializers.URLField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    industry_sector = serializers.CharField(max_length=75, required=False, allow_blank=True)
    location = serializers.CharField(max_length=150, required=False, allow_blank=True)
    district_id = serializers.CharField(max_length=36, required=False, allow_blank=True)

    legal_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    tax_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    company_size = serializers.CharField(max_length=50, required=False, allow_blank=True)
    linkedin_url = serializers.URLField(required=False, allow_blank=True)
    verification_document_url = serializers.URLField(required=False, allow_blank=True)

    def validate_name(self, value):
        clean_value = value.strip()
        if not clean_value:
            raise serializers.ValidationError("Company name cannot be empty")
        return clean_value

    def validate_poc_name(self, value):
        clean_value = value.strip()
        if not clean_value:
            raise serializers.ValidationError("POC name cannot be empty")
        return clean_value

    def validate_poc_email(self, value):
        clean_value = value.strip().lower()
        if User.every.filter(email__iexact=clean_value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return clean_value

    def validate_poc_phone(self, value):
        clean_value = value.strip()
        if not clean_value:
            return ""
        if not PHONE_REGEX.match(clean_value):
            raise serializers.ValidationError(
                "Phone number must contain 8 to 15 digits and may start with '+'"
            )
        if User.every.filter(mobile=clean_value).exists():
            raise serializers.ValidationError("A user with this phone number already exists")
        return clean_value

    def validate_district_id(self, value):
        clean_value = value.strip()
        if not clean_value:
            return ""
        if not District.objects.filter(id=clean_value).exists():
            raise serializers.ValidationError("Invalid district")
        return clean_value

    def validate(self, attrs):
        if Company.objects.filter(name__iexact=attrs["name"]).exists():
            raise serializers.ValidationError({"name": ["Company name already exists"]})

        organization_exists = Organization.objects.filter(
            org_type=OrganizationType.COMPANY.value,
            title__iexact=attrs["name"],
        ).exists()
        if not organization_exists and not attrs.get("district_id"):
            raise serializers.ValidationError(
                {
                    "district_id": [
                        "district_id is required when no matching company organization exists"
                    ]
                }
            )
        return attrs


class CompanyVerificationListSerializer(serializers.ModelSerializer):
    poc_name = serializers.CharField(source="company_user_id.full_name", read_only=True)
    poc_email = serializers.CharField(source="company_user_id.email", read_only=True)
    poc_phone = serializers.CharField(source="company_user_id.mobile", read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "poc_name",
            "poc_email",
            "poc_phone",
            "website_link",
            "industry_sector",
            "location",
            "verification_requested_at",
            "verified_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]


class CompanyOnboardingStatusSerializer(serializers.ModelSerializer):
    poc_name = serializers.CharField(source="company_user_id.full_name", read_only=True)
    poc_email = serializers.CharField(source="company_user_id.email", read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "poc_name",
            "poc_email",
            "rejection_reason",
            "verification_requested_at",
            "verified_at",
            "created_at",
            "updated_at",
        ]


class CompanyVerificationActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs["action"] == "reject" and not attrs.get("reason", "").strip():
            raise serializers.ValidationError({"reason": ["Reason is required when rejecting"]})
        return attrs
