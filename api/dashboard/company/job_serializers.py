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

    def validate(self, data):
        """
        PRD §5.3 — structured skill tagging: a 'skill' rule must reference a
        real, active Skill id rather than free text, so job matching/search
        can rely on it being a valid Skill reference.
        """
        if data.get('rule_type') == 'skill':
            from db.skill import Skill
            if not Skill.objects.filter(id=data.get('rule_value'), is_active=True).exists():
                raise serializers.ValidationError(
                    {"rule_value": "rule_value must be an active Skill id when rule_type is 'skill'."}
                )
        return data

class JobCreateSerializer(serializers.ModelSerializer):
    rules = JobRuleSerializer(many=True, required=False)

    class Meta:
        model = CompanyJob
        fields = [
            'id', 'title', 'experience', 'job_description', 'location',
            'salary_range', 'job_type', 'duration_value',
            'duration_unit', 'hourly_rate', 'deliverables', 'stipend',
            'certificate_provided', 'expires_at', 'rules'
        ]
        read_only_fields = ['id']

    def validate(self, data):
        """Enforce that duration_value and duration_unit are always provided together."""
        duration_value = data.get('duration_value')
        duration_unit = data.get('duration_unit')
        if duration_value is not None and not duration_unit:
            raise serializers.ValidationError(
                {"duration_unit": "duration_unit is required when duration_value is provided."}
            )
        if duration_unit and duration_value is None:
            raise serializers.ValidationError(
                {"duration_value": "duration_value is required when duration_unit is provided."}
            )
        return data

    def create(self, validated_data):
        rules_data = validated_data.pop('rules', [])
        user_id = self.context.get('user_id')
        is_owner = self.context.get('is_owner', False)

        company = self.context.get('company')
        if not company:
            raise serializers.ValidationError("You do not have a verified company profile or lack permissions.")

        if is_owner:
            validated_data['status'] = 'Draft'
        else:  # Mentor is creating the job
            validated_data['status'] = 'Pending Approval'

        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id

        job = CompanyJob.objects.create(company=company, created_by_id=user_id, **validated_data)

        for rule_data in rules_data:
            CompanyJobRule.objects.create(job=job, **rule_data)

        return job

class JobUpdateSerializer(serializers.ModelSerializer):
    rules = JobRuleSerializer(many=True, required=False)
    status = serializers.ChoiceField(choices=CompanyJob.Status.choices, required=False)

    class Meta:
        model = CompanyJob
        fields = [
            'title', 'experience', 'job_description', 'location',
            'salary_range', 'job_type', 'status', 'duration_value',
            'duration_unit', 'hourly_rate', 'deliverables', 'stipend',
            'certificate_provided', 'expires_at', 'rules'
        ]

    def validate(self, data):
        """Enforce that duration_value and duration_unit are always provided together."""
        duration_value = data.get('duration_value')
        duration_unit = data.get('duration_unit')
        if duration_value is not None and not duration_unit:
            raise serializers.ValidationError(
                {"duration_unit": "duration_unit is required when duration_value is provided."}
            )
        if duration_unit and duration_value is None:
            raise serializers.ValidationError(
                {"duration_value": "duration_value is required when duration_unit is provided."}
            )
        return data

    def update(self, instance, validated_data):
        rules_data = validated_data.pop('rules', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.updated_by_id = self.context.get('user_id')
        instance.save()
        
        if rules_data is not None:
            # Non-destructive update: match by rule_type, update value; delete stale; create new
            existing_rules = {r.rule_type: r for r in CompanyJobRule.objects.filter(job=instance)}
            incoming_types = set()
            for rule_data in rules_data:
                rule_type = rule_data['rule_type']
                incoming_types.add(rule_type)
                if rule_type in existing_rules:
                    existing_rules[rule_type].rule_value = rule_data['rule_value']
                    existing_rules[rule_type].save(update_fields=['rule_value'])
                else:
                    CompanyJobRule.objects.create(job=instance, **rule_data)
            # Delete rules that were removed
            stale_types = set(existing_rules.keys()) - incoming_types
            CompanyJobRule.objects.filter(job=instance, rule_type__in=stale_types).delete()
                
        return instance

def check_job_eligibility(user_id, job):
    """
    PRD §5.3 — evaluate every eligibility rule on a job for a given learner
    and return the full result set (not just the first failure), so it can
    be shown to a learner *before* they apply rather than only as a
    silent-rejection validation error at apply-time.
    """
    from db.skill import Skill
    from db.achievement import UserSkillProgress

    wallet = Wallet.objects.filter(user_id=user_id).first()
    user_karma = wallet.karma if wallet else 0
    lvl_link = UserLvlLink.objects.filter(user_id=user_id).first()
    user_level = lvl_link.level.level_order if (lvl_link and lvl_link.level) else 0

    results = []
    for rule in CompanyJobRule.objects.filter(job=job):
        met, message = True, None
        if rule.rule_type == 'min_karma':
            met = user_karma >= int(rule.rule_value)
            message = f"Insufficient Karma. Minimum {rule.rule_value} required." if not met else None
        elif rule.rule_type == 'max_karma':
            met = user_karma <= int(rule.rule_value)
            message = f"Exceeds Karma limit. Maximum {rule.rule_value} allowed." if not met else None
        elif rule.rule_type == 'min_level':
            met = user_level >= int(rule.rule_value)
            message = f"Insufficient Level. Minimum Level {rule.rule_value} required." if not met else None
        elif rule.rule_type == 'max_level':
            met = user_level <= int(rule.rule_value)
            message = f"Exceeds Level limit. Maximum Level {rule.rule_value} allowed." if not met else None
        elif rule.rule_type == 'skill':
            met = UserSkillProgress.objects.filter(user_id=user_id, skill_id=rule.rule_value).exists()
            if not met:
                skill = Skill.objects.filter(id=rule.rule_value).first()
                message = f"Requires the '{skill.name if skill else rule.rule_value}' skill."
        results.append({
            "rule_type": rule.rule_type,
            "rule_value": rule.rule_value,
            "met": met,
            "message": message,
        })
    return results


class JobListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source='company.name', read_only=True)
    company_logo = serializers.CharField(source='company.logo', read_only=True)
    rules = JobRuleSerializer(many=True, read_only=True)
    eligibility = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True, default=None)
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True, default=None)

    class Meta:
        model = CompanyJob
        fields = [
            'id', 'company_name', 'company_logo', 'title', 'experience',
            'job_description', 'location', 'salary_range', 'job_type',
            'status', 'duration_value', 'duration_unit', 'hourly_rate',
            'deliverables', 'stipend', 'certificate_provided', 'rules',
            'eligibility', 'created_at', 'created_by_name', 'rejection_reason',
            'approved_at', 'approved_by_name', 'expires_at'
        ]

    def get_eligibility(self, obj):
        """
        PRD §5.3 — only computed when a learner_id is passed via context
        (e.g. the public job browse/apply surfaces); omitted (None) for the
        company's own dashboard views where eligibility is not meaningful.
        """
        learner_id = self.context.get("learner_id")
        if not learner_id:
            return None
        results = check_job_eligibility(learner_id, obj)
        return {"eligible": all(r["met"] for r in results), "rules": results}

class JobApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserJobApplication
        fields = ['id', 'job', 'resume_link', 'cover_letter', 'status']
        read_only_fields = ['id', 'status']
        extra_kwargs = {
        'resume_link': {
        'required': True,
        'allow_blank': False,
        'allow_null': False,
        'error_messages': {
            'required': 'A resume link is required to apply for this job.'
        }
    },
}


    def validate(self, data):
        user_id = self.context.get('user_id')
        job = data.get('job')

        if UserJobApplication.objects.filter(user_id=user_id, job=job).exists():
            raise serializers.ValidationError("You have already applied for this job.")

        # Conflict-of-interest (PRD §5.2/§15): a company's own owner, accepted
        # co-admin, or active COMPANY_MENTOR cannot apply to its own postings.
        from api.dashboard.company.company_views import is_company_owner_or_admin
        from api.dashboard.mentor.dash_mentor_helper import get_mentor_scopes
        from db.user import MentorScopeGrant
        is_staff = is_company_owner_or_admin(user_id, job.company)
        if not is_staff and job.company.org_id:
            is_staff = (MentorScopeGrant.ScopeType.COMPANY_MENTOR, str(job.company.org_id)) in get_mentor_scopes(user_id)
        if is_staff:
            raise serializers.ValidationError("You cannot apply to your own company's job posting.")

        for rule_result in check_job_eligibility(user_id, job):
            if not rule_result["met"]:
                raise serializers.ValidationError(rule_result["message"])

        return data

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['user_id'] = user_id
        return UserJobApplication.objects.create(**validated_data)


class JobVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["Active", "Rejected"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("status") == "Rejected" and not data.get("rejection_reason", "").strip():
            raise serializers.ValidationError({"rejection_reason": "Rejection reason is required when rejecting."})
        return data

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        status = validated_data.get("status")
        now = DateTimeUtils.get_current_utc_time()

        instance.status = status
        instance.updated_by_id = user_id
        instance.updated_at = now

        if status == "Active":
            instance.rejection_reason = None
            instance.approved_by_id = user_id
            instance.approved_at = now
        elif status == "Rejected":
            instance.rejection_reason = validated_data.get("rejection_reason")
            instance.approved_by_id = None
            instance.approved_at = None

        instance.save()
        return instance

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

    def validate(self, data):
        """Require rejection_reason when setting status to Rejected.
        Prevent any status change once the application is Selected."""
        # Once selected, status cannot be changed
        if self.instance and self.instance.status == 'Selected' and 'status' in data:
            raise serializers.ValidationError(
                {"status": "Cannot change the status of a selected application."}
            )

        status = data.get('status')
        rejection_reason = data.get('rejection_reason', '').strip() if data.get('rejection_reason') else ''
        if status == 'Rejected' and not rejection_reason:
            raise serializers.ValidationError(
                {"rejection_reason": "A rejection reason is required when rejecting an application."}
            )
        return data

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
