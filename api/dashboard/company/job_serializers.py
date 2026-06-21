import uuid
from rest_framework import serializers
from db.job import CompanyJob, CompanyJobRule, UserJobApplication
from db.company import Company
from db.user import User
from db.task import Wallet, UserLvlLink, UserIgLink
from utils.utils import DateTimeUtils

class JobRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyJobRule
        fields = ['id', 'rule_type', 'rule_value']
        read_only_fields = ['id']

class JobCreateSerializer(serializers.ModelSerializer):
    rules = JobRuleSerializer(many=True, required=False)

    class Meta:
        model = CompanyJob
        fields = [
            'id', 'title', 'experience', 'job_description', 'location',
            'salary_range', 'job_type', 'duration_value',
            'duration_unit', 'hourly_rate', 'deliverables', 'stipend',
            'certificate_provided', 'rules'
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        rules_data = validated_data.pop('rules', [])
        user_id = self.context.get('user_id')

        company = self.context.get('company')
        if not company:
            raise serializers.ValidationError("You do not have a verified company profile or lack permissions.")

        # Jobs are always created as Draft; status can only be changed via PATCH.
        validated_data['status'] = 'Draft'

        job = CompanyJob.objects.create(company=company, **validated_data)

        for rule_data in rules_data:
            CompanyJobRule.objects.create(job=job, **rule_data)

        return job

class JobUpdateSerializer(serializers.ModelSerializer):
    rules = JobRuleSerializer(many=True, required=False)

    class Meta:
        model = CompanyJob
        fields = [
            'title', 'experience', 'job_description', 'location', 
            'salary_range', 'job_type', 'status', 'duration_value', 
            'duration_unit', 'hourly_rate', 'deliverables', 'stipend', 
            'certificate_provided', 'rules'
        ]

    def update(self, instance, validated_data):
        rules_data = validated_data.pop('rules', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.updated_by = self.context.get('user_id')
        instance.save()
        
        if rules_data is not None:
            CompanyJobRule.objects.filter(job=instance).delete()
            for rule_data in rules_data:
                CompanyJobRule.objects.create(job=instance, **rule_data)
                
        return instance

class JobListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_logo = serializers.CharField(source='company.logo', read_only=True)
    rules = JobRuleSerializer(many=True, read_only=True)

    class Meta:
        model = CompanyJob
        fields = [
            'id', 'company_name', 'company_logo', 'title', 'experience', 
            'job_description', 'location', 'salary_range', 'job_type', 
            'status', 'duration_value', 'duration_unit', 'hourly_rate', 
            'deliverables', 'stipend', 'certificate_provided', 'rules',
            'created_at'
        ]

class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserJobApplication
        fields = ['id', 'job', 'resume_link', 'cover_letter', 'status']
        read_only_fields = ['id', 'status']

    def validate(self, data):
        user_id = self.context.get('user_id')
        job = data.get('job')

        if UserJobApplication.objects.filter(user_id=user_id, job=job).exists():
            raise serializers.ValidationError("You have already applied for this job.")

        user = User.objects.filter(id=user_id).first()
        wallet = Wallet.objects.filter(user_id=user_id).first()
        user_karma = wallet.karma if wallet else 0
        lvl_link = UserLvlLink.objects.filter(user_id=user_id).first()
        user_level = lvl_link.level.level_order if (lvl_link and lvl_link.level) else 0
        rules = CompanyJobRule.objects.filter(job=job)
        
        for rule in rules:
            if rule.rule_type == 'min_karma':
                if user_karma < int(rule.rule_value):
                    raise serializers.ValidationError(f"Insufficient Karma. Minimum {rule.rule_value} required.")
            elif rule.rule_type == 'max_karma':
                if user_karma > int(rule.rule_value):
                    raise serializers.ValidationError(f"Exceeds Karma limit. Maximum {rule.rule_value} allowed.")
            elif rule.rule_type == 'min_level':
                if user_level < int(rule.rule_value):
                    raise serializers.ValidationError(f"Insufficient Level. Minimum Level {rule.rule_value} required.")
            elif rule.rule_type == 'max_level':
                if user_level > int(rule.rule_value):
                    raise serializers.ValidationError(f"Exceeds Level limit. Maximum Level {rule.rule_value} allowed.")
                      
        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['user_id'] = user_id
        return UserJobApplication.objects.create(**validated_data)

class ApplicationTrackingSerializer(serializers.ModelSerializer):
    applicant_name = serializers.CharField(source='user.full_name', read_only=True)
    applicant_email = serializers.CharField(source='user.email', read_only=True)
    
    class Meta:
        model = UserJobApplication
        fields = [
            'id', 'job', 'applicant_name', 'applicant_email', 
            'resume_link', 'cover_letter', 'status', 'rejection_reason',
            'applied_at'
        ]
        read_only_fields = ['id', 'job', 'applicant_name', 'applicant_email', 'resume_link', 'cover_letter', 'applied_at']

    def update(self, instance, validated_data):
        instance.status = validated_data.get('status', instance.status)
        instance.rejection_reason = validated_data.get('rejection_reason', instance.rejection_reason)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

class UserApplicationResubmitSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserJobApplication
        fields = ['resume_link', 'cover_letter']

    def update(self, instance, validated_data):
        instance.resume_link = validated_data.get('resume_link', instance.resume_link)
        instance.cover_letter = validated_data.get('cover_letter', instance.cover_letter)
        instance.status = 'Pending'
        instance.rejection_reason = None
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

class UserAppliedJobsSerializer(serializers.ModelSerializer):
    job = JobListSerializer(read_only=True)

    class Meta:
        model = UserJobApplication
        fields = [
            'id', 'job', 'resume_link', 'cover_letter', 'status', 
            'rejection_reason', 'applied_at'
        ]

