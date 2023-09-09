import uuid
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils

from rest_framework import serializers

from db.organization import Organization, District, Zone, State, OrgAffiliation, Department


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


class DepartmentSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=True)
    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Department
        fields = ["id",
                  "title"]

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        validated_data['id'] = str(uuid.uuid4())
        validated_data['updated_by_id'] = user_id
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['created_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['title'] = self.data.get('title')
        return Department.objects.create(**validated_data)

    def update(self, instance, validated_data):
        updated_title = validated_data.get('title')
        instance.title = updated_title
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance
