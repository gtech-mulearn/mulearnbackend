import uuid

from django.utils.text import slugify
from rest_framework import serializers

from db.organization import District, State, Country
from db.partner import UserPartner
from db.user import Role, UserRoleLink
from utils.types import PartnerType, RoleType
from utils.utils import DateTimeUtils


class PartnerRegisterSerializer(serializers.ModelSerializer):
    """Used for POST /register/ (create)."""
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(), required=False, allow_null=True, source="district"
    )
    state_id = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True, source="state"
    )
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True, source="country"
    )

    class Meta:
        model = UserPartner
        fields = [
            "name", "description", "email", "logo", "short_pitch",
            "location", "district_id", "state_id", "country_id",
            "partner_type", "website_link", "social_links",
        ]

    def validate_partner_type(self, value):
        if value and value not in PartnerType.get_all_values():
            raise serializers.ValidationError(
                f"Invalid partner_type. Must be one of: {', '.join(PartnerType.get_all_values())}"
            )
        return value

    def create(self, validated_data):
        user_id = self.context["user_id"]

        base_slug = slugify(validated_data["name"])
        slug, counter = base_slug, 1
        while UserPartner.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        return UserPartner.objects.create(
            id=str(uuid.uuid4()),
            user_link_id=user_id,
            slug=slug,
            status="pending",
            submitted_at=DateTimeUtils.get_current_utc_time(),
            updated_by=user_id,
            **validated_data,
        )


class PartnerUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH /register/ and PATCH /profile/."""
    district_id = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(), required=False, allow_null=True, source="district"
    )
    state_id = serializers.PrimaryKeyRelatedField(
        queryset=State.objects.all(), required=False, allow_null=True, source="state"
    )
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), required=False, allow_null=True, source="country"
    )

    class Meta:
        model = UserPartner
        fields = [
            "name", "description", "email", "logo", "short_pitch",
            "location", "district_id", "state_id", "country_id",
            "partner_type", "website_link", "social_links",
        ]

    def validate_partner_type(self, value):
        if value and value not in PartnerType.get_all_values():
            raise serializers.ValidationError(
                f"Invalid partner_type. Must be one of: {', '.join(PartnerType.get_all_values())}"
            )
        return value

    def update(self, instance, validated_data):
        validated_data["updated_by"] = self.context.get("user_id", instance.user_link_id)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class PartnerStatusSerializer(serializers.ModelSerializer):
    """Minimal shape for GET /status/."""
    class Meta:
        model = UserPartner
        fields = ["status", "rejection_reason", "submitted_at", "verified_at"]


class PartnerDetailSerializer(serializers.ModelSerializer):
    """Full profile for GET /profile/ (authenticated partner)."""
    user_name = serializers.CharField(source="user_link.full_name", read_only=True)
    user_email = serializers.CharField(source="user_link.email", read_only=True)
    district_name = serializers.CharField(source="district.name", read_only=True, default=None)
    state_name = serializers.CharField(source="state.name", read_only=True, default=None)
    country_name = serializers.CharField(source="country.name", read_only=True, default=None)

    class Meta:
        model = UserPartner
        fields = [
            "id", "user_link_id", "user_name", "user_email", "name", "slug", "logo", "description", "email",
            "short_pitch", "location", "district_id", "district_name", "state_id", "state_name", "country_id", "country_name",
            "partner_type", "website_link", "social_links",
            "status", "rejection_reason", "submitted_at", "verified_at", "created_at",
        ]


class PublicPartnerProfileSerializer(serializers.ModelSerializer):
    """Public profile — exposes resolved location names, hides IDs and audit fields."""
    district = serializers.CharField(source="district.name", read_only=True, default=None)
    state = serializers.CharField(source="state.name", read_only=True, default=None)
    country = serializers.CharField(source="country.name", read_only=True, default=None)

    class Meta:
        model = UserPartner
        fields = [
            "name", "slug", "logo", "description", "short_pitch",
            "website_link", "location", "district", "state", "country",
            "partner_type", "social_links",
        ]


class PartnerListSerializer(serializers.ModelSerializer):
    """Summary row for admin GET /admin/list/."""
    user_name = serializers.CharField(source="user_link.full_name", read_only=True)
    user_email = serializers.CharField(source="user_link.email", read_only=True)

    class Meta:
        model = UserPartner
        fields = [
            "id", "name", "slug", "email", "partner_type", "location",
            "status", "user_link_id", "user_name", "user_email",
            "submitted_at", "verified_at",
        ]


class PartnerVerifySerializer(serializers.Serializer):
    """Admin PATCH /admin/<partner_id>/verify/ — approve or reject."""
    status = serializers.ChoiceField(choices=["verified", "rejected"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("status") == "verified":
            if not Role.objects.filter(title=RoleType.PARTNER.value).exists():
                raise serializers.ValidationError(
                    {"status": "Partner role not found in the database. Ensure the role has been seeded before approving."}
                )
        if data.get("status") == "rejected" and not data.get("rejection_reason"):
            raise serializers.ValidationError(
                {"rejection_reason": "Rejection reason is required when rejecting."}
            )
        return data

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        status = validated_data["status"]

        instance.status = status
        instance.updated_by = user_id

        if status == "verified":
            instance.verified_by = user_id
            instance.verified_at = DateTimeUtils.get_current_utc_time()

            # Assign the Partner role to the registering user
            partner_role = Role.objects.filter(title=RoleType.PARTNER.value).first()
            if partner_role:
                UserRoleLink.objects.update_or_create(
                    user=instance.user_link,
                    role=partner_role,
                    defaults={
                        "verified": True,
                        "created_by": instance.user_link,
                        "created_at": DateTimeUtils.get_current_utc_time(),
                    },
                )

        elif status == "rejected":
            instance.rejection_reason = validated_data.get("rejection_reason")

        instance.save()
        return instance
