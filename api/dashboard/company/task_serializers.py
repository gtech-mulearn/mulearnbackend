import uuid

from rest_framework import serializers

from db.task import TaskList
from db.skill import TaskSkillLink


class CompanyTaskCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for company task creation.
    Similar to mentor task creation but IG is optional and no IG validation.
    Locked fields (active, approval_status, requested_by, requested_at)
    are injected by the view via serializer.save(**overrides).
    """

    class Meta:
        model = TaskList
        fields = (
            "hashtag",
            "title",
            "karma",
            "usage_count",
            "description",
            "type",
            "level",
            "created_by",
            "updated_by",
        )
        extra_kwargs = {
            "ig": {"required": False, "allow_null": True},
        }

    def validate_hashtag(self, value):
        """Global hashtag uniqueness."""
        qs = TaskList.objects.filter(hashtag=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A task with this hashtag already exists."
            )
        return value


class CompanyTaskUpdateSerializer(serializers.ModelSerializer):
    """
    Partial update serializer — same writable fields as create except created_by.
    """

    class Meta:
        model = TaskList
        fields = (
            "hashtag",
            "title",
            "karma",
            "usage_count",
            "description",
            "type",
            "level",
            "updated_by",
        )
        extra_kwargs = {
            "ig": {"required": False, "allow_null": True},
        }

    def validate_hashtag(self, value):
        """Exclude current instance from uniqueness check on edit."""
        qs = TaskList.objects.filter(hashtag=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A task with this hashtag already exists."
            )
        return value


class CompanyTaskListSerializer(serializers.ModelSerializer):
    """
    Read-only list/detail serializer for company tasks.
    """
    channel = serializers.CharField(source="channel.name", required=False, default=None)
    type    = serializers.CharField(source="type.title")
    level   = serializers.CharField(source="level.name",  required=False, default=None)
    ig      = serializers.CharField(source="ig.name",     required=False, default=None)
    org     = serializers.CharField(source="org.title",   required=False, default=None)
    requested_by_name = serializers.CharField(
        source="requested_by.full_name", required=False, default=None
    )
    skills = serializers.SerializerMethodField()

    class Meta:
        model = TaskList
        fields = [
            "id",
            "hashtag",
            "discord_link",
            "title",
            "description",
            "karma",
            "channel",
            "type",
            "active",
            "variable_karma",
            "usage_count",
            "level",
            "org",
            "ig",
            "event",
            "bonus_karma",
            "bonus_time",
            "approval_status",
            "rejection_reason",
            "reviewed_at",
            "requested_by_name",
            "requested_at",
            "skills",
            "created_at",
            "updated_at",
        ]

    def get_skills(self, obj):
        """Return skills linked to this task."""
        skill_links = TaskSkillLink.objects.filter(task_id=obj.id).select_related("skill")
        return [
            {"id": link.skill.id, "name": link.skill.name, "code": link.skill.code}
            for link in skill_links
        ]


class CompanyTaskPatchSerializer(serializers.Serializer):
    """
    Validates the payload when a company updates an existing task.
    All fields are optional to support partial updates.
    """
    title       = serializers.CharField(max_length=75, required=False)
    hashtag     = serializers.CharField(max_length=75, required=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    karma       = serializers.IntegerField(min_value=1, required=False)
    ig_id       = serializers.CharField(max_length=36, required=False)
    type_id     = serializers.CharField(max_length=36, required=False)
    channel_id  = serializers.CharField(max_length=36, required=False, allow_null=True)
    level_id    = serializers.CharField(max_length=36, required=False, allow_null=True)

    def validate_hashtag(self, value):
        value = value.strip()
        if not value.startswith('#'):
            raise serializers.ValidationError("hashtag must start with '#'")
        
        # Unique validation excluding the current task instance
        task_id = self.context.get("task_id")
        from db.task import TaskList
        qs = TaskList.objects.filter(hashtag__iexact=value)
        if task_id:
            qs = qs.exclude(id=task_id)
        if qs.exists():
            raise serializers.ValidationError(f"A task with hashtag '{value}' already exists.")
        return value

    def validate_ig_id(self, value):
        from db.task import InterestGroup
        if not InterestGroup.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Interest Group with id '{value}' does not exist.")
        return value

    def validate_type_id(self, value):
        from db.task import TaskType
        if not TaskType.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"TaskType with id '{value}' does not exist.")
        return value

