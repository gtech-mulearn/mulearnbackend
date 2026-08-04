from rest_framework import serializers
from db.company import Collaboration


class CollaborationSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.name", read_only=True)
    company_logo = serializers.CharField(source="company.logo", read_only=True)
    responded_by_name = serializers.CharField(source="responded_by.full_name", read_only=True, default=None)

    class Meta:
        model = Collaboration
        fields = [
            "id", "company_name", "company_logo", "collab_type", "title", "description",
            "target_type", "target_org_id", "event_id", "status",
            "responded_by_name", "responded_at", "rejection_reason", "created_at",
        ]
