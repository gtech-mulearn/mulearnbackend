from rest_framework import serializers
from db.company import CompanyJob, CompanyJobRule
from db.skill import Skill
from db.task import InterestGroup
from db.achievement import Achievement
class JobRuleListSerializer(serializers.ModelSerializer):
    rule_name = serializers.SerializerMethodField()
    class Meta:
        model = CompanyJobRule
        fields = ["id", "rule_type", "rule_type_id","rule_name"]
    def get_rule_name(self, obj):
        if obj.rule_type == "skill":
            skill = Skill.objects.filter(id=obj.rule_type_id).first()
            return skill.name if skill else None

        elif obj.rule_type == "interest_group":
            group = InterestGroup.objects.filter(id=obj.rule_type_id).first()
            return group.name if group else None

        elif obj.rule_type == "achievement":
            achievement = Achievement.objects.filter(id=obj.rule_type_id).first()
            return achievement.name if achievement else None

        return None

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
        """Additional validation for rule data."""
        rule_type = data.get('rule_type')
        rule_type_id = data.get('rule_type_id')
        
        # Add validation based on rule_type if needed
        if rule_type == 'skill':
            # Validate that skill exists (if you have a Skill model)
            pass
        elif rule_type == 'interest_group':
            # Validate that interest group exists
            pass
        elif rule_type == 'achievement':
            # Validate that achievement exists
            pass
            
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
        """Additional validation and auto-fetch rule_name if not provided."""
        rule_type_id = data.get('rule_type_id')
        # rule_name = data.get('rule_name')
        
        # Get the rule_type from the instance being updated
        if hasattr(self, 'instance') and self.instance:
            rule_type = self.instance.rule_type
            
            # If rule_name is not provided, try to fetch it
            # if not rule_name:
            #     data['rule_name'] = self.get_rule_name(rule_type, rule_type_id)
        
        return data
    
    # def get_rule_name(self, rule_type, rule_type_id):
    #     """Fetch the rule name based on rule_type and rule_type_id."""
    #     try:
    #         if rule_type == 'skill':
    #             # Replace with actual skill model lookup
    #             return f"Skill_{rule_type_id}"
                
    #         elif rule_type == 'interest_group':
    #             # Replace with actual interest group model lookup
    #             return f"InterestGroup_{rule_type_id}"
                
    #         elif rule_type == 'achievement':
    #             # Replace with actual achievement model lookup
    #             return f"Achievement_{rule_type_id}"
                
    #     except Exception as e:
    #         print(f"Error fetching rule name: {str(e)}")
    #         return f"Unknown {rule_type}"
        
    #     return rule_type_id
