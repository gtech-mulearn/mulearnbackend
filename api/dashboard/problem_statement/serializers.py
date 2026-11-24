from django.utils import timezone
from rest_framework import serializers

from db.problem_statement import ProblemStatement, ProblemStatementInteraction
from utils.validators import validate_safe_url

MAX_SKILLS = 15


def _clean_skills(value):
    seen, cleaned = set(), []
    for skill in value:
        skill = skill.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            cleaned.append(skill)
    if len(cleaned) > MAX_SKILLS:
        raise serializers.ValidationError(f"At most {MAX_SKILLS} skills are allowed.")
    return cleaned


class ProblemStatementWriteSerializer(serializers.ModelSerializer):
    """Create / partial-update payload. Ownership fields are never accepted from the body."""
    skills = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False, allow_empty=True
    )

    class Meta:
        model = ProblemStatement
        fields = ["title", "description", "category", "skills", "deadline"]
        extra_kwargs = {
            "title": {"min_length": 5},
            "description": {"min_length": 20, "max_length": 20000},
        }

    def validate_skills(self, value):
        return _clean_skills(value)

    def validate_deadline(self, value):
        if value is not None and value <= timezone.now():
            raise serializers.ValidationError("Deadline must be in the future.")
        return value


class AdminProblemStatementWriteSerializer(ProblemStatementWriteSerializer):
    """
    Admin payload: also accepts ``muid`` to create / edit the statement on behalf of a user.
    Blank or null clears it. Resolution to a user happens in the view.
    """
    muid = serializers.CharField(max_length=100, required=False, allow_null=True, allow_blank=True)

    class Meta(ProblemStatementWriteSerializer.Meta):
        fields = [*ProblemStatementWriteSerializer.Meta.fields, "muid"]


class InteractionWriteSerializer(serializers.ModelSerializer):
    """
    `status` is optional and only "Trying" is accepted: Submitted is reachable
    only through the submission endpoint, which also stores the link.
    """
    status = serializers.ChoiceField(
        choices=[ProblemStatementInteraction.Status.TRYING], required=False
    )

    class Meta:
        model = ProblemStatementInteraction
        fields = ["status"]


class SubmissionWriteSerializer(serializers.ModelSerializer):
    """The link is required here even though the column is nullable (it is cleared on withdrawal)."""

    class Meta:
        model = ProblemStatementInteraction
        fields = ["submission_url"]
        extra_kwargs = {
            "submission_url": {"required": True, "allow_null": False, "allow_blank": False},
        }

    def validate_submission_url(self, value):
        return validate_safe_url(value)


class ProblemStatementSerializer(serializers.ModelSerializer):
    """
    Read serializer. Counts and the caller's own interaction are looked up once
    per page by the view and passed through the context, so list responses do
    not run a query per row.

    context: ``counts`` {statement_id: {status: n}}, ``my_interactions``
    {statement_id: status} (optional), ``show_audit`` bool.
    """
    company = serializers.SerializerMethodField()
    interaction_counts = serializers.SerializerMethodField()
    my_interaction = serializers.SerializerMethodField()
    is_open = serializers.SerializerMethodField()
    on_behalf_of = serializers.SerializerMethodField()

    class Meta:
        model = ProblemStatement
        fields = [
            "id", "title", "description", "category", "skills", "deadline", "status",
            "company", "on_behalf_of", "is_open", "interaction_counts", "my_interaction",
            "created_by", "created_at", "updated_by", "updated_at",
            "published_by", "published_at",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.context.get("show_audit"):
            for field in ("created_by", "updated_by", "published_by", "on_behalf_of"):
                self.fields.pop(field)
        if "my_interactions" not in self.context:
            self.fields.pop("my_interaction")

    def get_company(self, obj):
        # company is None also guards a source/company mismatch made outside the API
        # (the DB can't enforce it), so one bad row can't 500 the whole list.
        if obj.source == ProblemStatement.Source.MULEARN or obj.company is None:
            return {"id": None, "name": "muLearn", "logo": None}
        return {"id": obj.company_id, "name": obj.company.name, "logo": obj.company.logo}

    def get_on_behalf_of(self, obj):
        user = obj.on_behalf_of
        if user is None:
            return None
        return {"id": user.id, "muid": user.muid, "full_name": user.full_name}

    def get_interaction_counts(self, obj):
        counts = self.context.get("counts", {}).get(obj.id, {})
        return {status: counts.get(status, 0) for status in ProblemStatementInteraction.Status.values}

    def get_my_interaction(self, obj):
        return self.context["my_interactions"].get(obj.id)

    def get_is_open(self, obj):
        return obj.status == ProblemStatement.Status.PUBLISHED and (
            obj.deadline is None or obj.deadline > timezone.now()
        )
