import json

from rest_framework import serializers

from db.projects import (
    Project, ProjectImage, ProjectLink, ProjectSkillLink,
    Comment, Vote, ProjectMember,
)
from db.user import User
from db.skill import Skill


# ───── Member ─────────────────────────────────────────────

class ProjectMemberSerializer(serializers.ModelSerializer):
    is_linked = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()
    muid = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = ProjectMember
        fields = ["id", "is_linked", "user_id", "muid", "full_name",
                  "profile_pic", "external_name", "role", "created_at"]

    def get_is_linked(self, obj):
        return obj.user_id is not None

    def get_user_id(self, obj):
        return obj.user.id if obj.user else None

    def get_muid(self, obj):
        return obj.user.muid if obj.user else None

    def get_full_name(self, obj):
        return obj.user.full_name if obj.user else obj.external_name

    def get_profile_pic(self, obj):
        return obj.user.profile_pic if obj.user else None


class AddMemberSerializer(serializers.Serializer):
    """Accepts exactly one identity: muid, user_id, or external_name."""
    muid = serializers.CharField(required=False, allow_blank=False)
    user_id = serializers.CharField(required=False, allow_blank=False)
    external_name = serializers.CharField(required=False, allow_blank=False, max_length=100)
    role = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)

    def validate(self, data):
        identifiers = [k for k in ("muid", "user_id", "external_name") if data.get(k)]
        if len(identifiers) == 0:
            raise serializers.ValidationError("one of muid, user_id, or external_name is required")
        if len(identifiers) > 1:
            raise serializers.ValidationError("only one of muid, user_id, external_name may be set")

        if data.get("muid"):
            user = User.objects.filter(muid=data["muid"]).first()
            if not user:
                raise serializers.ValidationError("mulearn user not found for given muid")
            data["resolved_user"] = user
        elif data.get("user_id"):
            user = User.objects.filter(id=data["user_id"]).first()
            if not user:
                raise serializers.ValidationError("mulearn user not found for given user_id")
            data["resolved_user"] = user
        else:
            data["resolved_user"] = None  # external
        return data


# ───── Link & Skill ───────────────────────────────────────

class ProjectLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLink
        fields = ["id", "label", "url", "position"]


class ProjectSkillSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source="skill.id")
    name = serializers.CharField(source="skill.name")
    code = serializers.CharField(source="skill.code")
    icon = serializers.CharField(source="skill.icon")

    class Meta:
        model = ProjectSkillLink
        fields = ["id", "name", "code", "icon"]


# ───── Vote / Comment ─────────────────────────────────────

class VoteSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.full_name", read_only=True)
    user_id = serializers.CharField(source="user.id", read_only=True)

    class Meta:
        model = Vote
        fields = ["id", "vote", "project", "user", "user_id", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class CommentSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="user.full_name", read_only=True)
    user_id = serializers.CharField(source="user.id", read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "comment", "project", "user", "user_id", "created_at", "updated_at"]
        read_only_fields = ["created_at", "updated_at"]


class ProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImage
        fields = ["image"]


# ───── Project ────────────────────────────────────────────

class ProjectSerializer(serializers.ModelSerializer):
    updated_by = serializers.CharField(source="updated_by.full_name", read_only=True)
    created_by = serializers.CharField(source="created_by.full_name", read_only=True)
    created_by_id = serializers.CharField(source="created_by.id", read_only=True)
    logo = serializers.ImageField(max_length=None, use_url=True, required=False, allow_null=True)
    images = ProjectImageSerializer(many=True, read_only=True)
    links = ProjectLinkSerializer(many=True, read_only=True)
    skills = ProjectSkillSerializer(source="skill_links", many=True, read_only=True)
    members = ProjectMemberSerializer(many=True, read_only=True)
    votes = VoteSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id", "title", "description", "status",
            "logo", "images", "links", "skills",
            "members", "votes", "comments",
            "created_by", "created_by_id", "updated_by",
            "created_at", "updated_at",
        ]


class ProjectUpdateSerializer(serializers.ModelSerializer):
    """Accepts create / partial-update payload. Logo + images come as files;
    links + skills come as JSON-encoded strings (because the request is
    multipart/form-data)."""
    title = serializers.CharField(required=False, max_length=50)
    description = serializers.CharField(required=False)
    logo = serializers.ImageField(max_length=None, use_url=True, required=False, allow_null=True)
    status = serializers.ChoiceField(choices=Project.STATUS_CHOICES, required=False)
    links_json = serializers.CharField(required=False, allow_blank=True, write_only=True)
    skill_ids_json = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = Project
        fields = ["title", "description", "status", "logo", "links_json", "skill_ids_json"]

    def validate_links_json(self, value):
        if not value:
            return []
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            raise serializers.ValidationError("links_json must be valid JSON")
        if not isinstance(data, list):
            raise serializers.ValidationError("links_json must be a JSON array")
        for item in data:
            if not isinstance(item, dict) or "label" not in item or "url" not in item:
                raise serializers.ValidationError("each link must have label and url")
            if not item["label"].strip():
                raise serializers.ValidationError("link.label cannot be empty")
            if not item["url"].strip():
                raise serializers.ValidationError("link.url cannot be empty")
        return data

    def validate_skill_ids_json(self, value):
        if not value:
            return []
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            raise serializers.ValidationError("skill_ids_json must be valid JSON")
        if not isinstance(data, list) or not all(isinstance(x, str) for x in data):
            raise serializers.ValidationError("skill_ids_json must be a JSON array of skill id strings")
        existing = set(Skill.objects.filter(id__in=data).values_list("id", flat=True))
        missing = set(data) - existing
        if missing:
            raise serializers.ValidationError(f"unknown skill ids: {sorted(missing)}")
        return data

    def create(self, validated_data):
        # links_json and skill_ids_json are handled in the view after save();
        # strip them here so they never reach Model.objects.create().
        validated_data.pop("links_json", None)
        validated_data.pop("skill_ids_json", None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Same reason — strip the synthetic fields before the ORM update.
        validated_data.pop("links_json", None)
        validated_data.pop("skill_ids_json", None)
        return super().update(instance, validated_data)
