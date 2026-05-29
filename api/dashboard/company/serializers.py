import uuid
from rest_framework import serializers
from django.utils.text import slugify

from db.company import Company
from db.organization import Organization, District, State, Country
from db.user import UserRoleLink, Role
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils

def generate_unique_code():
    return uuid.uuid4().hex[:12]

class CompanyRegisterSerializer(serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(queryset=District.objects.all(), required=False, allow_null=True, source="district")
    state_id = serializers.PrimaryKeyRelatedField(queryset=State.objects.all(), required=False, allow_null=True, source="state")
    country_id = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True, source="country")

    class Meta:
        model = Company
        fields = [
            "name",
            "logo",
            "description",
            "short_pitch",
            "industry_sector",
            "website_link",
            "email",
            "location",
            "district_id",
            "state_id",
            "country_id",
            "legal_name",
            "registration_number",
            "tax_id",
            "company_size",
            "linkedin_url",
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery"
        ]

    def validate_short_pitch(self, value):
        if value:
            word_count = len(value.split())
            if word_count > 150:
                raise serializers.ValidationError("Short pitch must not exceed 150 words.")
        return value

    def create(self, validated_data):
        user_id = self.context["user_id"]
        
        # Auto-generate a slug from the company name
        base_slug = slugify(validated_data["name"])
        slug = base_slug
        counter = 1
        while Company.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        company = Company.objects.create(
            company_user_id=user_id,
            status="pending",
            slug=slug,
            verification_requested_at=DateTimeUtils.get_current_utc_time(),
            created_at=DateTimeUtils.get_current_utc_time(),
            updated_at=DateTimeUtils.get_current_utc_time(),
            updated_by=user_id,
            **validated_data
        )
        return company

class CompanyUpdateSerializer(serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(queryset=District.objects.all(), required=False, allow_null=True, source="district")
    state_id = serializers.PrimaryKeyRelatedField(queryset=State.objects.all(), required=False, allow_null=True, source="state")
    country_id = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True, source="country")

    class Meta:
        model = Company
        fields = [
            "name",
            "logo",
            "description",
            "short_pitch",
            "industry_sector",
            "website_link",
            "email",
            "location",
            "district_id",
            "state_id",
            "country_id",
            "legal_name",
            "registration_number",
            "tax_id",
            "company_size",
            "linkedin_url",
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery"
        ]

    def validate_short_pitch(self, value):
        if value:
            word_count = len(value.split())
            if word_count > 150:
                raise serializers.ValidationError("Short pitch must not exceed 150 words.")
        return value

    def update(self, instance, validated_data):
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_by'] = self.context.get("user_id", instance.company_user_id)
        
        # If the name changes, don't necessarily change the slug unless required, but let's keep slug static or regenerate if you want.
        # Usually slug shouldn't change to avoid breaking links.
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class CompanyListSerializer(serializers.ModelSerializer):
    company_user_name = serializers.CharField(source='company_user.full_name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True, default=None)
    state_name = serializers.CharField(source='district.zone.state.name', read_only=True, default=None)
    country_name = serializers.CharField(source='district.zone.state.country.name', read_only=True, default=None)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "email",
            "company_user_id",
            "company_user_name",
            "industry_sector",
            "company_size",
            "location",
            "district_name",
            "state_name",
            "country_name",
            "verification_requested_at",
            "verified_at"
        ]

class CompanyDetailSerializer(serializers.ModelSerializer):
    company_user_name = serializers.CharField(source='company_user.full_name', read_only=True)
    company_user_email = serializers.CharField(source='company_user.email', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True, default=None)

    class Meta:
        model = Company
        fields = "__all__"

class CompanyVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["verified", "rejected"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("status") == "rejected" and not data.get("rejection_reason"):
            raise serializers.ValidationError("Rejection reason is required when rejecting.")
        return data

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        status = validated_data.get("status")
        
        instance.status = status
        instance.updated_by = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        
        if status == "verified":
            instance.verified_by = user_id
            instance.verified_at = DateTimeUtils.get_current_utc_time()
            
            # 1. Create Organization Record if it doesn't exist
            # Check if there's already an org mapped to this company to avoid duplicates
            org = Organization.objects.filter(title=instance.name, org_type=OrganizationType.COMPANY.value).first()
            if not org:
                org_code = generate_unique_code()
                Organization.objects.create(
                    title=instance.name,
                    code=org_code,
                    org_type=OrganizationType.COMPANY.value,
                    district=instance.district,
                    created_by_id=user_id,
                    updated_by_id=user_id,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    updated_at=DateTimeUtils.get_current_utc_time()
                )
            
            # 2. Auto-assign Company role to the User
            company_role = Role.objects.filter(title=RoleType.COMPANY.value).first()
            if company_role:
                UserRoleLink.objects.update_or_create(
                    user=instance.company_user,
                    role=company_role,
                    defaults={
                        "verified": True, 
                        "created_by": instance.company_user,
                        "created_at": DateTimeUtils.get_current_utc_time()
                    }
                )
                
        elif status == "rejected":
            instance.rejection_reason = validated_data.get("rejection_reason")
            
        instance.save()
        return instance
