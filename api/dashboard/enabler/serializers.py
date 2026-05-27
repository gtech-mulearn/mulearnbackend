from rest_framework import serializers
from db.organization import Organization, EnablerCampusNote
from db.user import User

class EnablerCampusListSerializer(serializers.ModelSerializer):
    campus_code = serializers.ReadOnlyField(source="code")
    college_name = serializers.ReadOnlyField(source="title")
    zone = serializers.ReadOnlyField(source="district.zone.name")

    class Meta:
        model = Organization
        fields = ["id", "college_name", "campus_code", "zone", "org_type"]

class EnablerCampusNoteSerializer(serializers.ModelSerializer):
    enabler_name = serializers.CharField(source="enabler.full_name", read_only=True)
    
    class Meta:
        model = EnablerCampusNote
        fields = ["id", "enabler_name", "note", "status", "priority", "follow_up_date", "created_at", "updated_at"]
        read_only_fields = ["id", "enabler_name", "created_at", "updated_at"]

    def create(self, validated_data):
        enabler_id = self.context.get("enabler_id")
        campus_id = self.context.get("campus_id")
        
        note = EnablerCampusNote.objects.create(
            enabler_id=enabler_id,
            campus_id=campus_id,
            created_by_id=enabler_id,
            updated_by_id=enabler_id,
            **validated_data
        )
        return note

    def update(self, instance, validated_data):
        enabler_id = self.context.get("enabler_id")
        instance.updated_by_id = enabler_id
        return super().update(instance, validated_data)
