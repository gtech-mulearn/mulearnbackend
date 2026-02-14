from rest_framework import serializers
from db.company import CompanyJob


class CompanyJobListSerializer(serializers.ModelSerializer):
    """Serializer for listing company jobs."""
    
    class Meta:
        model = CompanyJob
        fields = [
            'id', 'title', 'job_type', 'location', 'salary_range', 
            'min_karma', 'min_level', 'status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyJobCreateSerializer(serializers.ModelSerializer):
    company_id = serializers.CharField(max_length=36)
    
    class Meta:
        model = CompanyJob
        fields = [
             'title', 'experience', 'job_description', 
            'location', 'salary_range', 'job_type', 'min_karma', 'min_level'
        ]
        extra_kwargs = {
            'title': {'required': True, 'max_length': 75},
            'job_type': {'required': True},
        }
    
    def validate_job_type(self, value):
        valid_types = [choice[0] for choice in CompanyJob.JOB_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError("job_type must be one of the allowed values")
        return value


class CompanyJobUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CompanyJob
        fields = [
            'title', 'experience', 'job_description', 
            'location', 'salary_range', 'job_type', 'min_karma', 'min_level'
        ]
        extra_kwargs = {
            'title': {'required': False, 'max_length': 75},
            'experience': {'required': False},
            'job_description': {'required': False},
            'location': {'required': False},
            'salary_range': {'required': False},
            'job_type': {'required': False},
            'min_karma': {'required': False},
            'min_level': {'required': False},
        }
    
    def validate_job_type(self, value):
        valid_types = [choice[0] for choice in CompanyJob.JOB_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError("job_type must be one of the allowed values")
        return value
    
    def validate(self, attrs):
        # Ensure at least one field is provided for update
        if not attrs:
            raise serializers.ValidationError("At least one valid field must be provided for update")
        return attrs