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

class StateSerializer(serializers.ModelSerializer):

    country_id = serializers.CharField(required=False)

    def validate_country_id(self, value):
        if country := Country.objects.filter(id=value).first():
            return country.id
        else:
            raise serializers.ValidationError("Country Does Not Exists")

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
        model = State
        fields = ["id", "name", "country_id"]


class ZoneSerializer(serializers.ModelSerializer):

    state_id = serializers.CharField(required=False)
        
    def validate_state_id(self, value):
        if state := State.objects.filter(id=value).first():
            return state.id
        else:
            raise serializers.ValidationError("State Does Not Exists")

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
        model = Zone
        fields = ["id", "name", "state_id"]

class DistrictSerializer(serializers.ModelSerializer):

    zone_id = serializers.CharField(required=False)
        
    def validate_zone_id(self, value):
        if zone := Zone.objects.filter(id=value).first():
            return zone.id
        else:
            raise serializers.ValidationError("Zone Does Not Exists")

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
        model = District
        fields = ["id", "name", "zone_id"]