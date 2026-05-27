import uuid

from rest_framework import serializers

from db.task import InterestGroup, TaskList, TaskType


class CompanyTaskSubmitSerializer(serializers.Serializer):
    """
    Validates the payload when a company submits a new task for admin review.
    The ig_id is required — all company-submitted tasks must belong to an IG.
    """
    title       = serializers.CharField(max_length=75)
    hashtag     = serializers.CharField(max_length=75)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    karma       = serializers.IntegerField(min_value=1)
    ig_id       = serializers.CharField(max_length=36)
    type_id     = serializers.CharField(max_length=36)
    channel_id  = serializers.CharField(max_length=36, required=False, allow_null=True)
    level_id    = serializers.CharField(max_length=36, required=False, allow_null=True)

    def validate_hashtag(self, value):
        value = value.strip()
        if not value.startswith('#'):
            raise serializers.ValidationError("hashtag must start with '#'")
        if TaskList.objects.filter(hashtag__iexact=value).exists():
            raise serializers.ValidationError(f"A task with hashtag '{value}' already exists.")
        return value

    def validate_ig_id(self, value):
        if not InterestGroup.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Interest Group with id '{value}' does not exist.")
        return value

    def validate_type_id(self, value):
        if not TaskType.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"TaskType with id '{value}' does not exist.")
        return value


class CompanyTaskListSerializer(serializers.ModelSerializer):
    """Read-only serializer for a company's submitted tasks."""
    ig_name     = serializers.SerializerMethodField()
    type_name   = serializers.SerializerMethodField()

    class Meta:
        model  = TaskList
        fields = [
            'id', 'title', 'hashtag', 'description', 'karma',
            'approval_status', 'rejection_reason',
            'ig_name', 'type_name',
            'active', 'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None

    def get_type_name(self, obj):
        return obj.type.title if obj.type else None
