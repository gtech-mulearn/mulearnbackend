from rest_framework import serializers

from db.company import Company


class CompanyProfileCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "name",
            "logo",
            "description",
            "industry_sector",
            "website_link",
            "email",
            "slug",
            "location",
            "legal_name",
            "registration_number",
            "tax_id",
            "company_size",
            "linkedin_url",
            "verification_document_url",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("name cannot be empty")
        return value

    def validate_slug(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("slug cannot be empty")
        return value

    def validate(self, attrs):
        if self.partial and not attrs:
            raise serializers.ValidationError(
                "At least one valid field must be provided for update"
            )
        return attrs


class CompanyProfileSerializer(serializers.ModelSerializer):
    company_user_id = serializers.CharField(source="company_user_id.id", read_only=True)

    class Meta:
        model = Company
        fields = [
            "id",
            "company_user_id",
            "name",
            "logo",
            "description",
            "industry_sector",
            "website_link",
            "email",
            "slug",
            "status",
            "location",
            "legal_name",
            "registration_number",
            "tax_id",
            "company_size",
            "linkedin_url",
            "verification_document_url",
            "verification_requested_at",
            "verified_at",
            "verified_by",
            "rejection_reason",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = fields


class PublicCompanyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "logo",
            "description",
            "industry_sector",
            "website_link",
            "slug",
            "location",
        ]
        read_only_fields = fields
