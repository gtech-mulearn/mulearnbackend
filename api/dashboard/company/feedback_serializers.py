from rest_framework import serializers
from db.company import CompanyFeedback


class CompanyFeedbackCreateSerializer(serializers.Serializer):
    """Documentation-only shape for the feedback submission payload (validated manually in the view)."""
    interaction_type = serializers.ChoiceField(choices=CompanyFeedback.InteractionType.choices)
    entity_id = serializers.CharField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)


class CompanyFeedbackSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(source="submitted_by.full_name", read_only=True)

    class Meta:
        model = CompanyFeedback
        fields = [
            "id", "interaction_type", "entity_id", "submitted_by_name",
            "rating", "comment", "created_at",
        ]
