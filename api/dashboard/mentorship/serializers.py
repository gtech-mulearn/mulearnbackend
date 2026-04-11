import uuid

from rest_framework import serializers

from db.user import User, UserMentor
from db.task import KarmaActivityLog, InterestGroup, MentorSession


class MentorStatusSerializer(serializers.ModelSerializer):
    is_mentor = serializers.SerializerMethodField()
    tier = serializers.SerializerMethodField()

    class Meta:
        model = UserMentor
        fields = [
            "is_mentor",
            "is_verified",
            "tier",
            "hours",
            "about",
            "reason",
        ]

    def get_is_mentor(self, obj):
        return True

    def get_tier(self, obj):
        return "Verified" if obj.is_verified else "Normal"


class MentorProfileUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserMentor
        fields = ["about", "reason", "hours"]
        extra_kwargs = {
            "about": {"required": False},
            "reason": {"required": False},
            "hours": {"required": False},
        }

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.about = validated_data.get("about", instance.about)
        instance.reason = validated_data.get("reason", instance.reason)
        instance.hours = validated_data.get("hours", instance.hours)
        instance.updated_by_id = user_id
        instance.save()
        return instance


class MentorSessionCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = MentorSession
        fields = [
            "mentee",
            "ig",
            "title",
            "description",
            "scheduled_at",
            "duration_minutes",
            "meeting_link",
        ]
        extra_kwargs = {
            "ig": {"required": False, "allow_null": True},
            "description": {"required": False, "allow_null": True},
            "meeting_link": {"required": False, "allow_null": True},
        }

    def validate_mentee(self, value):
        if not User.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("Mentee not found")
        return value

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["id"] = str(uuid.uuid4())
        validated_data["mentor_id"] = user_id
        validated_data["status"] = MentorSession.Status.SCHEDULED
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        return MentorSession.objects.create(**validated_data)


class MentorSessionListSerializer(serializers.ModelSerializer):
    mentee_id = serializers.CharField(source="mentee.id")
    mentee_name = serializers.CharField(source="mentee.full_name")
    ig_name = serializers.SerializerMethodField()

    class Meta:
        model = MentorSession
        fields = [
            "id",
            "mentee_id",
            "mentee_name",
            "ig_name",
            "title",
            "scheduled_at",
            "duration_minutes",
            "status",
            "meeting_link",
            "notes",
        ]

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None


class MentorSessionUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = MentorSession
        fields = ["status", "notes"]
        extra_kwargs = {
            "status": {"required": False},
            "notes": {"required": False},
        }

    def validate_status(self, value):
        if value not in (MentorSession.Status.COMPLETED, MentorSession.Status.CANCELLED):
            raise serializers.ValidationError("Status must be 'completed' or 'cancelled'")
        return value

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.status = validated_data.get("status", instance.status)
        instance.notes = validated_data.get("notes", instance.notes)
        instance.updated_by_id = user_id
        instance.save()
        return instance


class TaskQueueSerializer(serializers.ModelSerializer):
    mentee_id = serializers.CharField(source="user.id")
    mentee_name = serializers.CharField(source="user.full_name")
    task_id = serializers.CharField(source="task.id")
    task_title = serializers.CharField(source="task.title")
    task_hashtag = serializers.CharField(source="task.hashtag")
    task_karma = serializers.IntegerField(source="task.karma")
    ig_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = KarmaActivityLog
        fields = [
            "id",
            "mentee_id",
            "mentee_name",
            "task_id",
            "task_title",
            "task_hashtag",
            "task_karma",
            "ig_name",
            "proof_link",
            "remarks",
            "status",
            "created_at",
        ]

    def get_ig_name(self, obj):
        if obj.task and obj.task.ig:
            return obj.task.ig.name
        return None

    def get_status(self, obj):
        if obj.appraiser_approved is None:
            return "pending"
        return "approved" if obj.appraiser_approved else "rejected"
