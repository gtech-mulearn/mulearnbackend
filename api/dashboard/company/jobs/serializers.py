from rest_framework import serializers
from db.company import CompanyJob, Company


class CreateCompanyJobSerializer(serializers.ModelSerializer):
    company_id = serializers.CharField(write_only=True)

    class Meta:
        model = CompanyJob
        fields = [
            'company_id', 'title', 'experience', 'job_description', 
            'location', 'salary_range', 'job_type', 'min_karma', 'min_level'
        ]

    def validate_company_id(self, value):
        try:
            company = Company.objects.get(id=value)
            return company
        except Company.DoesNotExist:
            raise serializers.ValidationError("Company does not exist")

    def validate_job_type(self, value):
        valid_types = ['Hybrid', 'Full-Time', 'Remote', 'Part-Time', 'Internship', 'Gig']
        if value not in valid_types:
            raise serializers.ValidationError("job_type must be one of the allowed values")
        return value

    def validate_title(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("Title is mandatory")
        if len(value) > 75:
            raise serializers.ValidationError("Title must not exceed 75 characters")
        return value

    def create(self, validated_data):
        company = validated_data.pop('company_id')
        validated_data['company'] = company
        return super().create(validated_data)


class CompanyJobResponseSerializer(serializers.ModelSerializer):
    company_id = serializers.CharField(source='company.id', read_only=True)

    class Meta:
        model = CompanyJob
        fields = ['id', 'company_id', 'title', 'job_type', 'created_at']