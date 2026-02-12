from rest_framework import serializers
from db.company import CompanyJob


class CompanyJobCreateSerializer(serializers.ModelSerializer):
    company_id = serializers.CharField(max_length=36)
    
    class Meta:
        model = CompanyJob
        fields = [
            'company_id', 'title', 'experience', 'job_description', 
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