from datetime import date

from django.db.models import Avg
from rest_framework import serializers

from db.company import Company, CompanyJobApplication


class CompanyExtendedFieldsMixin:
    def validate_founded_year(self, value):
        if value is not None and (value < 1800 or value > date.today().year):
            raise serializers.ValidationError("founded_year must be between 1800 and the current year")
        return value

    def _validate_string_list(self, value, field_name):
        if value is None:
            return value
        if not isinstance(value, list):
            raise serializers.ValidationError(f"{field_name} must be a list")
        if len(value) > 30:
            raise serializers.ValidationError(f"{field_name} cannot contain more than 30 items")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise serializers.ValidationError(f"Each {field_name} item must be a non-empty string")
        return value

    def validate_tech_stack(self, value):
        return self._validate_string_list(value, "tech_stack")

    def validate_perks(self, value):
        return self._validate_string_list(value, "perks")


class CompanyProfileCreateUpdateSerializer(CompanyExtendedFieldsMixin, serializers.ModelSerializer):
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
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery",
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


def _company_stats(company):
    accepted_apps = CompanyJobApplication.objects.filter(
        job__company_id=company,
        status="accepted",
    )
    avg_karma = accepted_apps.aggregate(
        avg=Avg("applicant__wallet_user__karma")
    ).get("avg")
    return {
        "hire_count": accepted_apps.count(),
        "alumni_count": accepted_apps.filter(
            applicant__user_organization_link_user__is_alumni=True
        ).distinct().count(),
        "avg_karma_of_hires": round(avg_karma or 0),
        "campus_events_count": 0,
    }


class CompanyProfileSerializer(serializers.ModelSerializer):
    company_user_id = serializers.CharField(source="company_user_id.id", read_only=True)
    hire_count = serializers.SerializerMethodField()
    alumni_count = serializers.SerializerMethodField()
    avg_karma_of_hires = serializers.SerializerMethodField()
    campus_events_count = serializers.SerializerMethodField()

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
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery",
            "hire_count",
            "alumni_count",
            "avg_karma_of_hires",
            "campus_events_count",
            "verification_requested_at",
            "verified_at",
            "verified_by",
            "rejection_reason",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = fields

    def get_hire_count(self, obj):
        return _company_stats(obj)["hire_count"]

    def get_alumni_count(self, obj):
        return _company_stats(obj)["alumni_count"]

    def get_avg_karma_of_hires(self, obj):
        return _company_stats(obj)["avg_karma_of_hires"]

    def get_campus_events_count(self, obj):
        return _company_stats(obj)["campus_events_count"]


class PublicCompanyProfileSerializer(serializers.ModelSerializer):
    hire_count = serializers.SerializerMethodField()
    alumni_count = serializers.SerializerMethodField()
    avg_karma_of_hires = serializers.SerializerMethodField()
    campus_events_count = serializers.SerializerMethodField()

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
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery",
            "hire_count",
            "alumni_count",
            "avg_karma_of_hires",
            "campus_events_count",
        ]
        read_only_fields = fields

    def get_hire_count(self, obj):
        return _company_stats(obj)["hire_count"]

    def get_alumni_count(self, obj):
        return _company_stats(obj)["alumni_count"]

    def get_avg_karma_of_hires(self, obj):
        return _company_stats(obj)["avg_karma_of_hires"]

    def get_campus_events_count(self, obj):
        return _company_stats(obj)["campus_events_count"]
