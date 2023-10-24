import uuid

from django.db.models import Count
from rest_framework import serializers

from db.organization import Organization, District, Zone, State, OrgAffiliation, Department
from utils.permission import JWTUtils
from utils.types import OrganizationType


class InstitutionSerializer(serializers.ModelSerializer):
    affiliation = serializers.ReadOnlyField(source="affiliation.title")
    district = serializers.ReadOnlyField(source="district.name")
    zone = serializers.ReadOnlyField(source="district.zone.name")
    state = serializers.ReadOnlyField(source="district.zone.state.name")
    country = serializers.ReadOnlyField(source="district.zone.state.country.name")
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "title",
            "code",
            "affiliation",
            "district",
            "zone",
            "state",
            "country",
            "user_count"
        ]

    def get_user_count(self, obj):
        return obj.user_organization_link_org.annotate(
            user_count=Count(
                'user'
            )
        ).count()


class InstitutionCsvSerializer(serializers.ModelSerializer):
    affiliation = serializers.SlugRelatedField(
        many=False,
        read_only=True,
        slug_field="title"
    )

    district = serializers.ReadOnlyField(source="district.name")
    zone = serializers.ReadOnlyField(source="district.zone.name")
    state = serializers.ReadOnlyField(source="district.zone.state.name")
    country = serializers.ReadOnlyField(source="district.zone.state.country.name")
    user_count = serializers.SerializerMethodField()

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
            "user_count"
        ]

    def get_user_count(self, obj):
        return obj.user_organization_link_org.annotate(
            user_count=Count(
                'user'
            )
        ).count()


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


class InstitutionCreateUpdateSerializer(serializers.ModelSerializer):
    district = serializers.CharField(required=False)

    class Meta:
        model = Organization
        fields = [
            "title",
            "code",
            "org_type",
            "affiliation",
            "district"
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['id'] = str(uuid.uuid4())
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id

        return Organization.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        instance.title = validated_data.get('title', instance.title)
        instance.code = validated_data.get('code', instance.code)
        instance.affiliation = validated_data.get('affiliation', instance.affiliation)
        instance.updated_by_id = user_id
        instance.save()
        return instance

    def validate_org_type(self, organization):
        if organization == OrganizationType.COLLEGE.value:
            affiliation = self.initial_data.get('affiliation')
            org_affiliation = OrgAffiliation.objects.filter(
                id=affiliation
            ).first()

            if org_affiliation is None:
                raise serializers.ValidationError(
                    "Invalid organization affiliation"
                )
        return organization

    def validate_affiliation(self, affiliation_id):
        if self.initial_data.get('org_type') != OrganizationType.COLLEGE.value:
            return None
        return affiliation_id


class AffiliationSerializer(serializers.ModelSerializer):
    label = serializers.ReadOnlyField(source='title')
    value = serializers.ReadOnlyField(source='id')

    class Meta:
        model = OrgAffiliation
        fields = [
            "value",
            "label"
        ]


class AffiliationCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAffiliation
        fields = [
            "title"
        ]

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id

        return OrgAffiliation.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        instance.title = validated_data.get('title', instance.title)
        instance.updated_by_id = user_id

        instance.save()
        return instance

    def validate_title(self, title):
        org_affiliation = OrgAffiliation.objects.filter(
            title=title
        ).first()

        if org_affiliation:
            raise serializers.ValidationError(
                "Affiliation already exist"
            )
        return title


class DepartmentSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=True)
    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Department
        fields = ["id",
                  "title"]

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        validated_data['title'] = self.data.get('title')
        validated_data['updated_by_id'] = user_id
        validated_data['created_by_id'] = user_id

        return Department.objects.create(**validated_data)

    def update(self, instance, validated_data):
        updated_title = validated_data.get('title')
        instance.title = updated_title
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        instance.updated_by_id = user_id
        instance.save()
        return instance
