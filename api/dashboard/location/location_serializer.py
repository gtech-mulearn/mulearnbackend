import uuid

from rest_framework import serializers

from db.organization import Country, District, State, Zone
from utils.utils import DateTimeUtils


class LocationSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")

    class Meta:
        model = Country
        fields = [
            "label",
            "value",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]


class CountryCreateEditSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")

    # value = serializers.CharField(source="id")
    class Meta:
        model = Country
        fields = ["label", "updated_by", "created_by"]


class StateRetrievalSerializer(serializers.ModelSerializer):
    country = serializers.CharField(source="country.name", required=False, default=None)
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")

    class Meta:
        model = State
        fields = [
            "label",
            "value",
            "country",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]


class StateCreateEditSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")

    # value = serializers.CharField(source="id")
    class Meta:
        model = State
        fields = ["label", "created_by", "updated_by"]


class ZoneRetrievalSerializer(serializers.ModelSerializer):
    country = serializers.CharField(
        source="state.country.name", required=False, default=None
    )
    state = serializers.CharField(source="state.name", required=False, default=None)
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")

    class Meta:
        model = Zone
        fields = [
            "label",
            "value",
            "country",
            "state",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]


class ZoneCreateEditSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    # value = serializers.CharField(source="id")

    class Meta:
        model = Zone
        fields = ["label", "created_by", "updated_by"]


class DistrictRetrievalSerializer(serializers.ModelSerializer):
    country = serializers.CharField(
        source="zone.state.country.name", required=False, default=None
    )
    state = serializers.CharField(
        source="zone.state.name", required=False, default=None
    )
    zone = serializers.CharField(source="zone.name", required=False, default=None)
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")
    created_by = serializers.CharField(source="created_by.fullname")
    updated_by = serializers.CharField(source="updated_by.fullname")

    class Meta:
        model = District
        fields = [
            "label",
            "value",
            "country",
            "state",
            "zone",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        ]


class DistrictCreateEditSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    # value = serializers.CharField(source="id")

    class Meta:
        model = District
        fields = ["label", "created_by", "updated_by"]
