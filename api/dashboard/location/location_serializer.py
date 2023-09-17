from rest_framework import serializers

from db.organization import Country, District, State, Zone
from utils.utils import DateTimeUtils


class CountryRetrievalSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")

    class Meta:
        model = Country
        fields = ["label", "value"]


class CountrySerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")

    class Meta:
        model = Country
        fields = ["label", "value"]

    def update(self, instance, validated_data):
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["updated_by_id"] = self.context.get("user_id")

        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data["updated_at"] = validated_data[
            "created_at"
        ] = DateTimeUtils.get_current_utc_time()

        validated_data["updated_by_id"] = validated_data[
            "created_by_id"
        ] = self.context.get("user_id")

        return super().create(validated_data)


class StateSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")

    class Meta:
        model = State
        fields = ["label", "value", "country"]

    def update(self, instance, validated_data):
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["updated_by_id"] = self.context.get("user_id")

        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data["updated_at"] = validated_data[
            "created_at"
        ] = DateTimeUtils.get_current_utc_time()

        validated_data["updated_by_id"] = validated_data[
            "created_by_id"
        ] = self.context.get("user_id")

        return super().create(validated_data)


class ZoneSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")

    class Meta:
        model = Zone
        fields = ["label", "value", "state"]

    def update(self, instance, validated_data):
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["updated_by_id"] = self.context.get("user_id")

        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data["updated_at"] = validated_data[
            "created_at"
        ] = DateTimeUtils.get_current_utc_time()

        validated_data["updated_by_id"] = validated_data[
            "created_by_id"
        ] = self.context.get("user_id")

        return super().create(validated_data)


class DistrictSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name")
    value = serializers.CharField(source="id")

    class Meta:
        model = District
        fields = ["label", "value", "zone"]

    def update(self, instance, validated_data):
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["updated_by_id"] = self.context.get("user_id")

        return super().update(instance, validated_data)

    def create(self, validated_data):
        validated_data["updated_at"] = validated_data[
            "created_at"
        ] = DateTimeUtils.get_current_utc_time()

        validated_data["updated_by_id"] = validated_data[
            "created_by_id"
        ] = self.context.get("user_id")

        return super().create(validated_data)
