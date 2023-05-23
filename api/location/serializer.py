from rest_framework import serializers
from db.organization import District, Zone, State, Country


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "updated_at", "created_at", "updated_by", "created_by"]


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "country", "updated_at", "created_at", "updated_by", "created_by"]


class ZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Zone
        fields = ["id", "name", "state", "updated_at", "created_at", "updated_by", "created_by"]


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ["id", "name", "zone", "updated_at", "created_at", "updated_by", "created_by"]

