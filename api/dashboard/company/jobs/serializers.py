from rest_framework import serializers
from db.company import CompanyJob, CompanyJobRule
from db.skill import Skill
from db.task import InterestGroup, TaskList
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
                return skill.name  # Use 'title' field for skills
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
    linked_task_info = serializers.SerializerMethodField()

    class Meta:
        model = CompanyJob
        fields = [
            'id', 'title', 'experience', 'job_description',
            'job_type', 'location', 'salary_range',
            'min_karma', 'min_level', 'status', 'created_at', 'updated_at',
            # Enhancement fields
            'karma_reward',
            'duration_value', 'duration_unit',
            'hourly_rate', 'deliverables',
            'stipend', 'certificate_provided',
            # Task-based hiring
            'requires_task_completion',
            'linked_task_info',
            'rules',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_linked_task_info(self, obj):
        """Return basic info about the linked task, or None."""
        if not obj.linked_task_id:
            return None
        try:
            task = TaskList.objects.get(id=obj.linked_task_id)
            return {
                'id': str(task.id),
                'hashtag': task.hashtag,
                'title': task.title,
                'karma': task.karma,
            }
        except TaskList.DoesNotExist:
            return None


class CompanyJobCreateSerializer(serializers.ModelSerializer):
    linked_task_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = CompanyJob
        fields = [
            'title', 'experience', 'job_description',
            'location', 'salary_range', 'job_type', 'min_karma', 'min_level',
            # Enhancement fields
            'karma_reward',
            'duration_value', 'duration_unit',
            'hourly_rate', 'deliverables',
            'stipend', 'certificate_provided',
            # Task-based hiring
            'linked_task_id', 'requires_task_completion',
        ]
        extra_kwargs = {
            'title':    {'required': True, 'max_length': 75},
            'job_type': {'required': True},
            'requires_task_completion': {'required': False},
        }

    def validate_job_type(self, value):
        valid_types = [choice[0] for choice in CompanyJob.JOB_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError("job_type must be one of the allowed values")
        return value

    def validate_karma_reward(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("karma_reward must be a non-negative integer")
        return value

    def validate_hourly_rate(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("hourly_rate must be greater than 0")
        return value

    def validate_deliverables(self, value):
        """Must be a list of non-empty strings."""
        if value is not None:
            if not isinstance(value, list):
                raise serializers.ValidationError("deliverables must be a JSON array of strings")
            for item in value:
                if not isinstance(item, str) or not item.strip():
                    raise serializers.ValidationError(
                        "Each deliverable must be a non-empty string"
                    )
        return value

    def validate(self, data):
        """Cross-field validation for structured and type-specific fields."""
        duration_value = data.get('duration_value')
        duration_unit  = data.get('duration_unit')

        # duration_value and duration_unit must come together
        if duration_value is not None and not duration_unit:
            raise serializers.ValidationError(
                {"duration_unit": "duration_unit is required when duration_value is provided"}
            )
        if duration_unit and duration_value is None:
            raise serializers.ValidationError(
                {"duration_value": "duration_value is required when duration_unit is provided"}
            )

        # Task-based hiring: if requires_task_completion, linked_task_id must be a live task
        requires_task = data.get('requires_task_completion', False)
        linked_task_id = data.get('linked_task_id')
        if requires_task:
            if not linked_task_id:
                raise serializers.ValidationError(
                    {"linked_task_id": "linked_task_id is required when requires_task_completion is True"}
                )
            task = TaskList.objects.filter(id=str(linked_task_id)).first()
            if not task:
                raise serializers.ValidationError(
                    {"linked_task_id": f"Task with id {linked_task_id} does not exist"}
                )
            if getattr(task, 'approval_status', 'approved') != 'approved' or not task.active:
                raise serializers.ValidationError(
                    {"linked_task_id": "Linked task must be approved and active"}
                )

        return data


class CompanyJobUpdateSerializer(serializers.ModelSerializer):
    linked_task_id = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = CompanyJob
        fields = [
            'title', 'experience', 'job_description',
            'location', 'salary_range', 'job_type', 'min_karma', 'min_level',
            # Enhancement fields
            'karma_reward',
            'duration_value', 'duration_unit',
            'hourly_rate', 'deliverables',
            'stipend', 'certificate_provided',
            # Task-based hiring
            'linked_task_id', 'requires_task_completion',
        ]
        extra_kwargs = {
            'title':                    {'required': False, 'max_length': 75},
            'experience':               {'required': False},
            'job_description':          {'required': False},
            'location':                 {'required': False},
            'salary_range':             {'required': False},
            'job_type':                 {'required': False},
            'min_karma':                {'required': False},
            'min_level':                {'required': False},
            'karma_reward':             {'required': False},
            'duration_value':           {'required': False},
            'duration_unit':            {'required': False},
            'hourly_rate':              {'required': False},
            'deliverables':             {'required': False},
            'stipend':                  {'required': False},
            'certificate_provided':     {'required': False},
            'requires_task_completion': {'required': False},
        }

    def validate_job_type(self, value):
        valid_types = [choice[0] for choice in CompanyJob.JOB_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError("job_type must be one of the allowed values")
        return value

    def validate_karma_reward(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("karma_reward must be a non-negative integer")
        return value

    def validate_hourly_rate(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("hourly_rate must be greater than 0")
        return value

    def validate_deliverables(self, value):
        if value is not None:
            if not isinstance(value, list):
                raise serializers.ValidationError("deliverables must be a JSON array of strings")
            for item in value:
                if not isinstance(item, str) or not item.strip():
                    raise serializers.ValidationError(
                        "Each deliverable must be a non-empty string"
                    )
        return value

    def validate(self, data):
        """Ensure at least one field is provided, and duration fields are consistent."""
        if not data:
            raise serializers.ValidationError("At least one valid field must be provided for update")

        duration_value = data.get('duration_value')
        duration_unit  = data.get('duration_unit')

        # Allow partial updates: only validate pairing when BOTH are in this request
        if duration_value is not None and duration_unit is not None:
            pass  # both provided — valid
        elif duration_value is not None and 'duration_unit' in data and data['duration_unit'] is None:
            raise serializers.ValidationError(
                {"duration_unit": "duration_unit cannot be null when duration_value is provided"}
            )
        elif duration_unit and 'duration_value' in data and data['duration_value'] is None:
            raise serializers.ValidationError(
                {"duration_value": "duration_value cannot be null when duration_unit is provided"}
            )

        # Task-based hiring validation (same as create)
        requires_task = data.get('requires_task_completion')
        linked_task_id = data.get('linked_task_id')
        if requires_task:
            if not linked_task_id:
                raise serializers.ValidationError(
                    {"linked_task_id": "linked_task_id is required when requires_task_completion is True"}
                )
            task = TaskList.objects.filter(id=str(linked_task_id)).first()
            if not task:
                raise serializers.ValidationError(
                    {"linked_task_id": f"Task with id {linked_task_id} does not exist"}
                )
            if getattr(task, 'approval_status', 'approved') != 'approved' or not task.active:
                raise serializers.ValidationError(
                    {"linked_task_id": "Linked task must be approved and active"}
                )

        return data

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
        fields = ['rule_type','rule_type_id']
    
    def validate_rule_type_id(self, value):
        """Validate that the rule_type_id exists."""
        if not value or not value.strip():
            raise serializers.ValidationError("rule_type_id cannot be empty")
        return value.strip()
    
    def validate(self, data):
        """Validate that the rule_type_id exists for the current rule_type."""
        
        
        rule_type = data.get('rule_type', self.instance.rule_type)
        rule_type_id = data.get('rule_type_id', self.instance.rule_type_id)
            
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
  
