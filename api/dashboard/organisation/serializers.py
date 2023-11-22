import uuid

from django.db.models import Count
from rest_framework import serializers
from django.db import models

from db.organization import (
    Organization,
    District,
    Zone,
    State,
    OrgAffiliation,
    Department,
    OrgKarmaType,
    OrgKarmaLog,
)
from utils.permission import JWTUtils
from utils.types import OrganizationType
from django.db import transaction
from django.forms.models import model_to_dict


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
            "user_count",
        ]

    def get_user_count(self, obj):
        return obj.user_organization_link_org.annotate(user_count=Count("user")).count()


# class InstitutionSerializer(serializers.ModelSerializer):
#     affiliation = serializers.SlugRelatedField(
#         many=False, read_only=True, slug_field="title"
#     )
#
#     district = serializers.ReadOnlyField(source="district.name")
#     zone = serializers.ReadOnlyField(source="district.zone.name")
#     state = serializers.ReadOnlyField(source="district.zone.state.name")
#     country = serializers.ReadOnlyField(source="district.zone.state.country.name")
#     user_count = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Organization
#         fields = [
#             "id",
#             "title",
#             "code",
#             "affiliation",
#             "org_type",
#             "district",
#             "zone",
#             "state",
#             "country",
#             "user_count",
#         ]
#
#     def get_user_count(self, obj):
#         return len({link.user for link in obj.user_organization_link_org.all()})


class StateSerializer(serializers.ModelSerializer):
    country = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="name"
    )

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
        fields = ["title", "code", "org_type", "affiliation", "district"]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["id"] = str(uuid.uuid4())
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id

        return Organization.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.title = validated_data.get("title", instance.title)
        instance.code = validated_data.get("code", instance.code)
        instance.affiliation = validated_data.get("affiliation", instance.affiliation)
        instance.updated_by_id = user_id
        instance.save()
        return instance

    def validate_org_type(self, organization):
        if organization == OrganizationType.COLLEGE.value:
            affiliation = self.initial_data.get("affiliation")
            org_affiliation = OrgAffiliation.objects.filter(id=affiliation).first()

            if org_affiliation is None:
                raise serializers.ValidationError("Invalid organization affiliation")
        return organization

    def validate_district(self, value):
        district = District.objects.filter(id=value).first()

        if district is None:
            raise serializers.ValidationError("Invalid district")

        return district

    def validate_affiliation(self, affiliation_id):
        if self.initial_data.get("org_type") != OrganizationType.COLLEGE.value:
            return None
        return affiliation_id


class AffiliationSerializer(serializers.ModelSerializer):
    label = serializers.ReadOnlyField(source="title")
    value = serializers.ReadOnlyField(source="id")

    class Meta:
        model = OrgAffiliation
        fields = ["value", "label"]


class AffiliationCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgAffiliation
        fields = ["title"]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id

        return OrgAffiliation.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.title = validated_data.get("title", instance.title)
        instance.updated_by_id = user_id

        instance.save()
        return instance

    def validate_title(self, title):
        org_affiliation = OrgAffiliation.objects.filter(title=title).first()

        if org_affiliation:
            raise serializers.ValidationError("Affiliation already exist")

        return title


class DepartmentSerializer(serializers.ModelSerializer):
    title = serializers.CharField(required=True)
    id = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = Department
        fields = ["id", "title"]

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get("request"))
        validated_data["title"] = self.data.get("title")
        validated_data["updated_by_id"] = user_id
        validated_data["created_by_id"] = user_id

        return Department.objects.create(**validated_data)

    def update(self, instance, validated_data):
        updated_title = validated_data.get("title")
        instance.title = updated_title
        user_id = JWTUtils.fetch_user_id(self.context.get("request"))
        instance.updated_by_id = user_id
        instance.save()
        return instance


class InstitutionPrefillSerializer(serializers.ModelSerializer):
    affiliation_id = serializers.CharField(source="affiliation.id", allow_null=True)
    affiliation_name = serializers.CharField(source="affiliation.name", allow_null=True)
    district_id = serializers.CharField(source="district.id", allow_null=True)
    district_name = serializers.CharField(source="district.name", allow_null=True)
    zone_id = serializers.CharField(source="district.zone.id", allow_null=True)
    zone_name = serializers.CharField(source="district.zone.name", allow_null=True)
    state_id = serializers.CharField(source="district.state.id", allow_null=True)
    state_name = serializers.CharField(source="district.state.name", allow_null=True)
    country_id = serializers.CharField(
        source="district.state.country.id", allow_null=True
    )
    country_name = serializers.CharField(
        source="district.state.country.name", allow_null=True
    )

    class Meta:
        model = Organization
        fields = [
            "id",
            "title",
            "code",
            "affiliation_id",
            "affiliation_name",
            "district_id",
            "district_name",
            "zone_id",
            "zone_name",
            "state_id",
            "state_name",
            "country_id",
            "country_name",
        ]


class OrganizationMergerSerializer(serializers.Serializer):
    update_summary = serializers.SerializerMethodField()
    source_org = serializers.SlugRelatedField(
        slug_field="code",
        queryset=Organization.objects.all(),
        write_only=True,
        error_messages={
            "does_not_exist": "An organization with the given code doesn't exist",
        },
    )

    def validate_source_org(self, attrs):
        if self.instance.code == attrs.code:
            raise serializers.ValidationError(
                "You can't merge an organization into itself."
            )
        return super().validate(attrs)

    def get_update_summary(self, instance):
        update_summary = []

        # Simulate the transaction
        for relation in Organization._meta.related_objects:
            if isinstance(
                relation,
                (models.ForeignKey, models.OneToOneField, models.ManyToManyField),
            ):
                related_model = relation.related_model
                related_field_name = relation.field.name
            elif isinstance(relation, (models.ManyToOneRel, models.ManyToManyRel)):
                related_model = relation.related_model
                related_field_name = next(
                    (
                        field.name
                        for field in related_model._meta.fields
                        if isinstance(field, models.ForeignKey)
                        and field.related_model == Organization
                    ),
                    None,
                )
            else:
                continue

            if not related_field_name:
                continue

            if existing_relations := related_model.objects.filter(
                **{related_field_name: instance}
            ):
                update_summary.append(
                    {
                        "model": related_model._meta.model_name,
                        "field_name": related_field_name,
                        "count": existing_relations.count(),
                        "action": (
                            "delete"
                            if isinstance(
                                relation, (models.OneToOneField, models.OneToOneRel)
                            )
                            else "update"
                        ),
                        "instance_ids": list(
                            existing_relations.values_list("pk", flat=True)
                        ),
                    }
                )

        return update_summary

    def update(self, instance, validated_data):
        with transaction.atomic():
            source_org = validated_data["source_org"]

            for relation in Organization._meta.related_objects:
                # Determine related model and related field name
                if isinstance(
                    relation,
                    (models.ForeignKey, models.OneToOneField, models.ManyToManyField),
                ):
                    related_model = relation.related_model
                    related_field_name = relation.field.name
                elif isinstance(relation, (models.ManyToOneRel, models.ManyToManyRel)):
                    related_model = relation.related_model
                    # Find the related field in the related model that links back to Organization
                    related_field_name = next(
                        (
                            field.name
                            for field in related_model._meta.fields
                            if isinstance(field, models.ForeignKey)
                            and field.related_model == Organization
                        ),
                        None,
                    )

                # Skip if we couldn't determine the related field
                if not related_field_name:
                    continue

                # Prepare filter and update arguments
                filter_kwargs = {related_field_name: source_org}
                update_kwargs = {related_field_name: instance}

                # Handle OneToOne relationships: delete existing relation if it points to the instance
                if isinstance(relation, (models.OneToOneField, models.OneToOneRel)):
                    if existing_relation := related_model.objects.filter(
                        **{related_field_name: instance}
                    ).first():
                        existing_relation.delete()

                # Update the relations in the related model
                related_model.objects.filter(**filter_kwargs).update(**update_kwargs)

            # Delete the organization that needs to be removed
            source_org.delete()

        return instance


class OrganizationKarmaTypeGetPostPatchDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrgKarmaType
        fields = [
            "title",
            "karma",
            "description",
        ]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["updated_by_id"] = user_id
        validated_data["created_by_id"] = user_id

        return OrgKarmaType.objects.create(**validated_data)


class OrganizationKarmaLogGetPostPatchDeleteSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrgKarmaLog
        fields = [
            "org",
            "karma",
            "type",
        ]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["updated_by_id"] = user_id
        validated_data["created_by_id"] = user_id

        return OrgKarmaLog.objects.create(**validated_data)

class OrganizationImportSerializer(serializers.ModelSerializer):
    created_by_id = serializers.CharField(required=True, allow_null=False)
    updated_by_id = serializers.CharField(required=True, allow_null=False)
    affiliation_id = serializers.CharField(required=False, allow_null=True)
    district_id = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "title",
            "code",
            "org_type",
            "affiliation_id",
            "district_id",
            "created_by_id",
            "updated_by_id",
        ]

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['affiliation_id'] = instance.affiliation.title if instance.affiliation else None
        representation['district_id'] = instance.district.name if instance.district else None

        return representation