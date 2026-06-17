from rest_framework import serializers

from db.intern import InternGuildMinute
from utils.types import InternGuild


class InternGuildMinuteSerializer(serializers.ModelSerializer):
    """Serializer for reading guild minutes (GET responses)."""
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = InternGuildMinute
        fields = [
            'id', 'guild', 'date', 'title', 'minutes',
            'created_by_name', 'created_at', 'updated_at',
        ]

    def get_created_by_name(self, obj):
        return obj.created_by.full_name if obj.created_by else None


class InternGuildMinuteCreateUpdateSerializer(serializers.Serializer):
    """Serializer for validating incoming POST/PUT data."""
    guild = serializers.ChoiceField(choices=InternGuild.get_all_values())
    date = serializers.DateField()
    title = serializers.CharField(max_length=200)
    minutes = serializers.CharField()

    def validate_minutes(self, value):
        if not value.strip():
            raise serializers.ValidationError("Minutes content cannot be blank.")
        return value
