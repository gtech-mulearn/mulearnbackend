from rest_framework import serializers
from organization.models import Organization, District, Zone, State, Country


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["name"]


class StateSerializer(serializers.ModelSerializer):
    country = CountrySerializer(many=False, read_only=True)

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

    # Slug method works fine....but this cannot satisfy nested requirements
    # district = serializers.SlugRelatedField(
    #     many=False,
    #     read_only=True,
    #     slug_field='name'
    #  )

    district = DistrictSerializer(many=False, read_only=True)

    class Meta:
        model = Organization
        fields = ["title", "code", "affiliation", "district"]
