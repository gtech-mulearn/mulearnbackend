from rest_framework import serializers

from db.organization import Organization, District, Zone, State, OrgAffiliation


# from organization.models import Organization, District, Zone, State, Country, OrgAffiliation


class StateSerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(many=False, read_only=True, slug_field="name")

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
        many=False, read_only=True, slug_field="title"
    )
    district = serializers.ReadOnlyField(source="district.name")
    zone = serializers.ReadOnlyField(source="district.zone.name")
    state = serializers.ReadOnlyField(source="district.zone.state.name")
    country = serializers.ReadOnlyField(source="district.zone.state.country.name")

    class Meta:
        model = Organization
        fields = [
            "id",
            "title",
            "code",
            "affiliation",
            "org_type",
            "district",
            "zone",
            "state",
            "country",
        ]


class PostOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = "__all__"


class AffiliationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAffiliation
        fields = "__all__"
