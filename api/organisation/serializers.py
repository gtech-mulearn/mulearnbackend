from rest_framework import serializers

from db.organization import Organization


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"
