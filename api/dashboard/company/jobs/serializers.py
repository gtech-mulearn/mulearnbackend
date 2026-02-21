from rest_framework import serializers
from db.company import CompanyJob, CompanyJobRule
from db.skill import Skill
from db.task import InterestGroup
from db.achievement import Achievement
class JobRuleListSerializer(serializers.ModelSerializer):
    rule_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CompanyJobRule
        fields = ["id", "rule_type", "rule_type_id", "rule_name"]
    
    def get_rule_name(self, obj):
        """Use cached_name if available, otherwise fall back to database query."""
        
        # 1. First try to use cached data from optimization
        if hasattr(obj, 'cached_name'):
            return obj.cached_name
        
        # 2. Fallback to database query (will cause N+1 queries)
        if obj.rule_type == "skill":
            try:
                skill = Skill.objects.get(id=obj.rule_type_id)
                return skill.title  # Use 'title' field for skills
            except Skill.DoesNotExist:
                return f"Unknown Skill ({obj.rule_type_id})"
                
        elif obj.rule_type == "interest_group":
            try:
                group = InterestGroup.objects.get(id=obj.rule_type_id)
                return group.name
            except InterestGroup.DoesNotExist:
                return f"Unknown Interest Group ({obj.rule_type_id})"
                
        elif obj.rule_type == "achievement":
            try:
                achievement = Achievement.objects.get(id=obj.rule_type_id)
                return achievement.name
            except Achievement.DoesNotExist:
                return f"Unknown Achievement ({obj.rule_type_id})"
        
        return f"Unknown Rule Type: {obj.rule_type}"

class CompanyJobListSerializer(serializers.ModelSerializer):
    """Serializer for listing company jobs."""
    rules = JobRuleListSerializer(many=True, read_only=True)
    class Meta:
        model = CompanyJob
        fields = [
            'id', 'title', 'job_type', 'location', 'salary_range', 
            'min_karma', 'min_level', 'status', 'created_at', 'updated_at',
              'rules'

        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class CompanyJobCreateSerializer(serializers.ModelSerializer):
    # company_id = serializers.CharField(max_length=36)
    
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

class JobRuleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating job rules."""
    
    RULE_TYPE_CHOICES = [
        ('skill', 'Skill'),
        ('interest_group', 'Interest Group'),
        ('achievement', 'Achievement'),
    ]
    
    rule_type = serializers.ChoiceField(choices=RULE_TYPE_CHOICES)
    rule_type_id = serializers.CharField(max_length=255)
    
    class Meta:
        model = CompanyJobRule
        fields = ['rule_type', 'rule_type_id']
    
    def validate(self, data):
        """Validate that the referenced objects actually exist."""
        rule_type = data.get('rule_type')
        rule_type_id = data.get('rule_type_id')
        
        if rule_type == 'skill':
            if not Skill.objects.filter(id=rule_type_id).exists():
                raise serializers.ValidationError({
                    'rule_type_id': f'Skill with ID {rule_type_id} does not exist'
                })
                
        elif rule_type == 'interest_group':
            if not InterestGroup.objects.filter(id=rule_type_id).exists():
                raise serializers.ValidationError({
                    'rule_type_id': f'Interest Group with ID {rule_type_id} does not exist'
                })
                
        elif rule_type == 'achievement':
            if not Achievement.objects.filter(id=rule_type_id).exists():
                raise serializers.ValidationError({
                    'rule_type_id': f'Achievement with ID {rule_type_id} does not exist'
                })
        
        return data


class JobRuleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating job rules."""
    
    rule_type_id = serializers.CharField(max_length=255)
    # rule_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    
    class Meta:
        model = CompanyJobRule
        fields = ['rule_type_id']
    
    def validate_rule_type_id(self, value):
        """Validate that the rule_type_id exists."""
        if not value or not value.strip():
            raise serializers.ValidationError("rule_type_id cannot be empty")
        return value.strip()
    
    def validate(self, data):
        """Validate that the rule_type_id exists for the current rule_type."""
        rule_type_id = data.get('rule_type_id')
        
        # Get the rule_type from the instance being updated
        if hasattr(self, 'instance') and self.instance:
            rule_type = self.instance.rule_type
            
            # Validate the new rule_type_id exists
            if rule_type == 'skill':
                if not Skill.objects.filter(id=rule_type_id).exists():
                    raise serializers.ValidationError({
                        'rule_type_id': f'Skill with ID {rule_type_id} does not exist'
                    })
                    
            elif rule_type == 'interest_group':
                if not InterestGroup.objects.filter(id=rule_type_id).exists():
                    raise serializers.ValidationError({
                        'rule_type_id': f'Interest Group with ID {rule_type_id} does not exist'
                    })
                    
            elif rule_type == 'achievement':
                if not Achievement.objects.filter(id=rule_type_id).exists():
                    raise serializers.ValidationError({
                        'rule_type_id': f'Achievement with ID {rule_type_id} does not exist'
                    })
        
        return data
  
