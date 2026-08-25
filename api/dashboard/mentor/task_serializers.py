import uuid

from rest_framework import serializers

from db.task import TaskList, InterestGroup, UserIgLink
from db.skill import Skill, TaskSkillLink
from utils.validators import validate_safe_text, enforce_max_length


class MentorTaskCreateSerializer(serializers.ModelSerializer):
    """
    Mirrors admin TaskModifySerializer field-for-field.
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
            "ig",
            "created_by",
            "updated_by",
        )
        extra_kwargs = {
            "ig": {"required": True, "allow_null": False},
        }

    def validate_hashtag(self, value):
        """Must start with '#' (same convention as admin/company task creation);
        global hashtag uniqueness — same rule as admin. Not run through
        validate_safe_text: its SQL-injection heuristic bans a bare '#',
        which every valid hashtag necessarily starts with.
        """
        value = value.strip()
        if not value.startswith('#'):
            raise serializers.ValidationError("hashtag must start with '#'")
        qs = TaskList.objects.filter(hashtag=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A task with this hashtag already exists."
            )
        return value

    def validate_title(self, value):
        validate_safe_text(value)
        return value

    def validate_description(self, value):
        if value:
            validate_safe_text(value)
            enforce_max_length(value, 5000)
        return value

    def validate_ig(self, value):
        """Mentor must be an active MENTOR member of the selected IG."""
        user_id = self.context.get("user_id")
        if not UserIgLink.objects.filter(
            user_id=user_id,
            ig=value,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                "You are not assigned as a mentor for this Interest Group."
            )
        return value


class MentorTaskUpdateSerializer(serializers.ModelSerializer):
    """
    Partial update serializer — same writable fields as create.
    The view injects approval_status / active / review-reset fields via save().
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
            "ig",
            "updated_by",
        )

    def validate_hashtag(self, value):
        """Must start with '#'; exclude current instance from uniqueness check on edit."""
        value = value.strip()
        if not value.startswith('#'):
            raise serializers.ValidationError("hashtag must start with '#'")
        qs = TaskList.objects.filter(hashtag=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A task with this hashtag already exists."
            )
        return value

    def validate_title(self, value):
        validate_safe_text(value)
        return value

    def validate_description(self, value):
        if value:
            validate_safe_text(value)
            enforce_max_length(value, 5000)
        return value

    def validate_ig(self, value):
        """Mentor must still belong to the IG even on edit."""
        user_id = self.context.get("user_id")
        if not UserIgLink.objects.filter(
            user_id=user_id,
            ig=value,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                "You are not assigned as a mentor for this Interest Group."
            )
        return value


class MentorTaskListSerializer(serializers.ModelSerializer):
    """
    Read-only list/detail serializer — mirrors admin TaskListSerializer.
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
        """Return skills linked to this task — same as admin TaskListSerializer."""
        skill_links = TaskSkillLink.objects.filter(task_id=obj.id).select_related("skill")
        return [
            {"id": link.skill.id, "name": link.skill.name, "code": link.skill.code}
            for link in skill_links
        ]


class MentorIGDropdownSerializer(serializers.ModelSerializer):
    """Minimal IG serializer for the mentor-scoped dropdown."""

    class Meta:
        model = InterestGroup
        fields = ["id", "name"]
