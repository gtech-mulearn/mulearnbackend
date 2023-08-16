from rest_framework import serializers
from utils.utils import DateTimeUtils
from db.organization import District, Zone, State, Country


class CountrySerializer(serializers.ModelSerializer):
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

    class Meta:
        model = Country
        fields = ["id", "name"]
