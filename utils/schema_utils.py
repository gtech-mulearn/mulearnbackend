"""Shared serializers for @extend_schema CustomResponse envelope documentation."""
from rest_framework import serializers


class MessageSerializer(serializers.Serializer):
    general = serializers.ListField(child=serializers.CharField(), allow_empty=True, required=False)


class CustomResponseSerializer(serializers.Serializer):
    """Matches the standard CustomResponse envelope returned by all API views."""
    hasError = serializers.BooleanField(default=False)
    statusCode = serializers.IntegerField(
        default=200,
        help_text="Application-level status code (200 on success, 400 on failure)."
    )
    message = MessageSerializer()
    response = serializers.JSONField(
        help_text="Free-form response payload; shape varies per endpoint."
    )
