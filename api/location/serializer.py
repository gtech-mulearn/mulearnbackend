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


class UserCountrySerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source='name')
    class Meta:
        model = Country
        fields = ["countryName"]


class UserStateSerializer(serializers.ModelSerializer):
    zoneName = serializers.CharField(source='name')
    class Meta:
        model = State
        fields = ["zoneName"]


class UserZoneSerializer(serializers.ModelSerializer):
    zoneName = serializers.CharField(source='name')
    class Meta:
        model = Zone
        fields = ["zoneName"]
