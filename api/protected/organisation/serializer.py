from rest_framework import serializers

from db.organization import Organization, District, Zone, State


class StateSerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field='name'
    )

    class Meta:
        model = State
        fields = ["name", "country"]


class ZoneSerializer(serializers.ModelSerializer):
    state = StateSerializer(many=False, read_only=True)

    class Meta:
        model = Zone
        fields = ["name", "state"]


class DistrictSerializer(serializers.ModelSerializer):
    zone = ZoneSerializer(many=False, read_only=True)

    class Meta:
        model = District
        fields = ["name", "zone"]


class OrganisationSerializer(serializers.ModelSerializer):
    affiliation = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field='title'
    )

    district = DistrictSerializer(many=False, read_only=True)

    class Meta:
        model = Organization
        fields = ["id", "title", "code", "affiliation", "district"]


class InstitutesRetrivalSerializer(serializers.ModelSerializer):
    district = serializers.CharField(source='district.name')

    class Meta:
        model = Organization
        fields = ["id", "title", "district"]
