from rest_framework import serializers
from organization.models import Organization


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
