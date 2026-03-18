from rest_framework import serializers
import json

from db.task import InterestGroup


class InterestGroupSerializer(serializers.ModelSerializer):

    updated_by = serializers.CharField(source="updated_by.full_name")
    created_by = serializers.CharField(source="created_by.full_name")
    members = serializers.SerializerMethodField()
    category = serializers.ChoiceField(
        choices=["maker", "coder", "creative", "manager", "others"]
    )

    class Meta:
        model = InterestGroup
        fields = [
            "id",
            "name",
            "resource",
            "about",
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
            "icon",
            "code",
            "category",
            "members",
            "updated_by",
            "updated_at",
            "created_by",
            "created_at",
        ]

    def get_members(self, obj):
        return obj.user_ig_link_ig.all().count()

    def to_representation(self, instance):
        """Convert JSON-serialized text fields back to Python objects for API output."""
        data = super().to_representation(instance)
        json_fields = [
            "prerequisites",
            "career_opportunities",
            "top_blogs",
            "people_to_follow",
            "mentors",
            "leads",
        ]

        for field in json_fields:
            val = data.get(field)
            if isinstance(val, str) and val:
                try:
                    parsed = json.loads(val)
                    data[field] = parsed
                except Exception:
                    # leave as-is (plain string)
                    pass

        return data


class InterestGroupCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterestGroup
        fields = [
            "name",
            "code",
            "category",
            "icon",
            "about",
            "prerequisites",
            "career_opportunities",
            "resource",
            "top_blogs",
            "people_to_follow",
            "leads",
            "mentors",
            "thinktank",
            "office_hours",
            "created_by",
            "updated_by",
        ]


class IGTopContributorSerializer(serializers.Serializer):
    full_name = serializers.CharField()
    muid = serializers.CharField()
    karma_earned = serializers.IntegerField()


class IGTaskSummarySerializer(serializers.Serializer):
    ig_id = serializers.CharField()
    ig_name = serializers.CharField()
    ig_code = serializers.CharField()
    total_tasks_completed = serializers.IntegerField()
    total_karma_awarded = serializers.IntegerField()
    unique_contributors = serializers.IntegerField()
    top_contributors = IGTopContributorSerializer(many=True)
    date_range = serializers.DictField(child=serializers.DateField(allow_null=True), allow_null=True)
