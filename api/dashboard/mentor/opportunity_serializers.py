from rest_framework import serializers
from db.mentor import IgOpportunity
from utils.utils import DateTimeUtils


class IgOpportunityListSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source='ig.name', read_only=True, default=None)
    org_name = serializers.CharField(source='org.title', read_only=True, default=None)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)

    class Meta:
        model = IgOpportunity
        fields = [
            "id", "ig", "ig_name", "org", "org_name", "type", "title",
            "description", "eligibility", "application_url",
            "starts_at", "ends_at", "status",
            "created_by_name", "created_at", "updated_at",
        ]


class IgOpportunityCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IgOpportunity
        fields = [
            "id", "ig", "org", "type", "title", "description",
            "eligibility", "application_url", "starts_at", "ends_at",
        ]
        read_only_fields = ["id"]

    def validate(self, data):
        if not data.get("ig") and not data.get("org"):
            raise serializers.ValidationError("Either ig or org must be set.")
        return data

    def create(self, validated_data):
        user_id = self.context["user_id"]
        now = DateTimeUtils.get_current_utc_time()
        # Always created DRAFT regardless of any status in the payload —
        # mirrors CompanyJobAPI's "always Draft" pattern.
        return IgOpportunity.objects.create(
            status=IgOpportunity.Status.DRAFT,
            created_by_id=user_id,
            updated_by_id=user_id,
            **validated_data,
        )


class IgOpportunityUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = IgOpportunity
        fields = [
            "title", "description", "eligibility", "application_url",
            "starts_at", "ends_at",
        ]

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by_id = user_id
        instance.save()
        return instance
