# qseverse/serializers.py

from rest_framework import serializers

class SubjectInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(required=False)

class CredentialInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    description = serializers.CharField()

class IssueVCSerializer(serializers.Serializer):
    subject_info = SubjectInfoSerializer()
    credential_info = CredentialInfoSerializer()
    template_id = serializers.CharField()
