import uuid
from rest_framework import serializers
from django.db import transaction
from django.utils.text import slugify

from db.company import Company
from db.organization import Organization, District, State, Country
from db.user import UserRoleLink, Role
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils

def generate_unique_code():
    """Generate a 12-char hex code guaranteed to be unique in Organization.code."""
    while True:
        code = uuid.uuid4().hex[:12]
        if not Organization.objects.filter(code=code).exists():
            return code

class CompanyRegisterSerializer(serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(queryset=District.objects.all(), required=False, allow_null=True, source="district")
    state_id = serializers.PrimaryKeyRelatedField(queryset=State.objects.all(), required=False, allow_null=True, source="state")
    country_id = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True, source="country")

    class Meta:
        model = Company
        fields = [
            "name",
            "logo",
            "description",
            "short_pitch",
            "industry_sector",
            "website_link",
            "email",
            "location",
            "district_id",
            "state_id",
            "country_id",
            "legal_name",
            "registration_number",
            "tax_id",
            "company_size",
            "linkedin_url",
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery"
        ]

    def validate_description(self, value):
        if value and len(value) > 5000:
            raise serializers.ValidationError("Description must not exceed 5000 characters.")
        return value

    def validate_culture_text(self, value):
        if value and len(value) > 3000:
            raise serializers.ValidationError("Culture text must not exceed 3000 characters.")
        return value

    def validate_perks(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError("Perks must not exceed 2000 characters.")
        return value

    def validate_testimonials(self, value):
        if value and len(value) > 3000:
            raise serializers.ValidationError("Testimonials must not exceed 3000 characters.")
        return value

    def validate_short_pitch(self, value):
        if value:
            word_count = len(value.split())
            if word_count > 150:
                raise serializers.ValidationError("Short pitch must not exceed 150 words.")
        return value

    def validate(self, data):
        """Enforce address hierarchy: district must belong to the supplied state/country."""
        district = data.get("district")
        state = data.get("state")
        country = data.get("country")

        if district and state:
            if not hasattr(district, 'zone') or district.zone.state_id != state.id:
                raise serializers.ValidationError(
                    {"district_id": "The selected district does not belong to the selected state."}
                )
        if district and country:
            if not hasattr(district, 'zone') or district.zone.state.country_id != country.id:
                raise serializers.ValidationError(
                    {"district_id": "The selected district does not belong to the selected country."}
                )
        return data

    def create(self, validated_data):
        user_id = self.context["user_id"]
        
        # Auto-generate a slug from the company name
        base_slug = slugify(validated_data["name"])
        slug = base_slug
        counter = 1
        while Company.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        company = Company.objects.create(
            company_user_id=user_id,
            status="pending",
            slug=slug,
            verification_requested_at=DateTimeUtils.get_current_utc_time(),
            created_at=DateTimeUtils.get_current_utc_time(),
            updated_at=DateTimeUtils.get_current_utc_time(),
            updated_by=user_id,
            **validated_data
        )
        return company

class CompanyUpdateSerializer(serializers.ModelSerializer):
    district_id = serializers.PrimaryKeyRelatedField(queryset=District.objects.all(), required=False, allow_null=True, source="district")
    state_id = serializers.PrimaryKeyRelatedField(queryset=State.objects.all(), required=False, allow_null=True, source="state")
    country_id = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all(), required=False, allow_null=True, source="country")

    class Meta:
        model = Company
        fields = [
            "name",
            "logo",
            "description",
            "short_pitch",
            "industry_sector",
            "website_link",
            "email",
            "location",
            "district_id",
            "state_id",
            "country_id",
            "legal_name",
            "registration_number",
            "tax_id",
            "company_size",
            "linkedin_url",
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery"
        ]

    def validate_description(self, value):
        if value and len(value) > 5000:
            raise serializers.ValidationError("Description must not exceed 5000 characters.")
        return value

    def validate_culture_text(self, value):
        if value and len(value) > 3000:
            raise serializers.ValidationError("Culture text must not exceed 3000 characters.")
        return value

    def validate_perks(self, value):
        if value and len(value) > 2000:
            raise serializers.ValidationError("Perks must not exceed 2000 characters.")
        return value

    def validate_testimonials(self, value):
        if value and len(value) > 3000:
            raise serializers.ValidationError("Testimonials must not exceed 3000 characters.")
        return value

    def validate_short_pitch(self, value):
        if value:
            word_count = len(value.split())
            if word_count > 150:
                raise serializers.ValidationError("Short pitch must not exceed 150 words.")
        return value

    def validate(self, data):
        """Enforce address hierarchy: district must belong to the supplied state/country."""
        district = data.get("district")
        state = data.get("state")
        country = data.get("country")

        if district and state:
            if not hasattr(district, 'zone') or district.zone.state_id != state.id:
                raise serializers.ValidationError(
                    {"district_id": "The selected district does not belong to the selected state."}
                )
        if district and country:
            if not hasattr(district, 'zone') or district.zone.state.country_id != country.id:
                raise serializers.ValidationError(
                    {"district_id": "The selected district does not belong to the selected country."}
                )
        return data

    def update(self, instance, validated_data):
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_by'] = self.context.get("user_id", instance.company_user_id)

        new_name = validated_data.get("name")
        rename = new_name and new_name != instance.name

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        with transaction.atomic():
            instance.save()

            if rename and instance.org:
                instance.org.title = new_name
                instance.org.updated_at = DateTimeUtils.get_current_utc_time()
                instance.org.save(update_fields=["title", "updated_at"])

        return instance

class CompanyListSerializer(serializers.ModelSerializer):
    company_user_name = serializers.CharField(source='company_user.full_name', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True, default=None)
    state_name = serializers.CharField(source='district.zone.state.name', read_only=True, default=None)
    country_name = serializers.CharField(source='district.zone.state.country.name', read_only=True, default=None)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "email",
            "company_user_id",
            "company_user_name",
            "industry_sector",
            "company_size",
            "location",
            "district_name",
            "state_name",
            "country_name",
            "verification_requested_at",
            "verified_at"
        ]

class CompanyDetailSerializer(serializers.ModelSerializer):
    company_user_name = serializers.CharField(source='company_user.full_name', read_only=True)
    company_user_email = serializers.CharField(source='company_user.email', read_only=True)
    district_name = serializers.CharField(source='district.name', read_only=True, default=None)

    class Meta:
        model = Company
        fields = "__all__"

class CompanyVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["verified", "rejected"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("status") == "rejected" and not data.get("rejection_reason"):
            raise serializers.ValidationError("Rejection reason is required when rejecting.")
        return data

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        status = validated_data.get("status")
        
        instance.status = status
        instance.updated_by = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        
        if status == "verified":
            instance.verified_by = user_id
            instance.verified_at = DateTimeUtils.get_current_utc_time()
            # Clear any stale rejection data from a previous rejection
            instance.rejection_reason = None

            # ── Ensure the company's Organization row exists ─────────────────
            org = instance.org or Organization.objects.filter(
                title=instance.name,
                org_type=OrganizationType.COMPANY.value,
            ).first()
            if not org:
                org_code = generate_unique_code()
                org = Organization.objects.create(
                    title=instance.name,
                    code=org_code,
                    org_type=OrganizationType.COMPANY.value,
                    district=instance.district,
                    created_by_id=user_id,
                    updated_by_id=user_id,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    updated_at=DateTimeUtils.get_current_utc_time(),
                )
            instance.org = org

            # ── Link the company creator to the org ──────────────────────────
            from db.organization import UserOrganizationLink
            UserOrganizationLink.objects.get_or_create(
                user=instance.company_user,
                org=org,
                defaults={
                    "verified": True,
                    "created_by_id": user_id,
                    "created_at": DateTimeUtils.get_current_utc_time(),
                },
            )

            # ── Grant the COMPANY role ───────────────────────────────────────
            company_role = Role.objects.filter(title=RoleType.COMPANY.value).first()
            if company_role:
                UserRoleLink.objects.update_or_create(
                    user=instance.company_user,
                    role=company_role,
                    defaults={
                        "verified": True,
                        "created_by": instance.company_user,
                        "created_at": DateTimeUtils.get_current_utc_time(),
                    },
                )

        elif status == "rejected":
            instance.rejection_reason = validated_data.get("rejection_reason")

        instance.save()
        return instance

class PublicCompanyProfileSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField(source='district.name', read_only=True, default=None)
    state_name = serializers.CharField(source='district.zone.state.name', read_only=True, default=None)
    country_name = serializers.CharField(source='district.zone.state.country.name', read_only=True, default=None)

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "slug",
            "logo",
            "description",
            "short_pitch",
            "industry_sector",
            "website_link",
            "email",
            "location",
            "district_name",
            "state_name",
            "country_name",
            "company_size",
            "linkedin_url",
            "founded_year",
            "remote_policy",
            "culture_text",
            "tech_stack",
            "perks",
            "testimonials",
            "gallery"
        ]


# ---------------------------------------------------------------------------
# Company Mentor serializers
# ---------------------------------------------------------------------------

from db.user import User as _User, UserMentor


class CompanyMentorNominateSerializer(serializers.Serializer):
    """Nominate an existing platform user as a Company Mentor for the company.

    The nominated user is identified by their ``muid`` (e.g. john-doe@mulearn)
    and must already be linked to the company's Organisation record.
    """

    muid = serializers.CharField(
        help_text="MuID of the platform user to nominate (e.g. john-doe@mulearn)."
    )
    reason = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Optional reason / note to pass with the nomination.",
    )

    def validate(self, data):
        company = self.context.get("company")
        muid = data.get("muid")

        # ── Resolve muid → User ──────────────────────────────────────────────
        user = _User.objects.filter(muid=muid).first()
        if not user:
            raise serializers.ValidationError(
                {"muid": f"No platform user found with muid '{muid}'."}
            )

        # ── Resolve company → Organization row ──────────────────────────────
        org = company.org
        if not org:
            raise serializers.ValidationError(
                "Company organization record not found. Ensure the company is verified."
            )

        # ── Validate org membership ──────────────────────────────────────────
        from db.organization import UserOrganizationLink as _UOL
        if not _UOL.objects.filter(user=user, org=org).exists():
            raise serializers.ValidationError(
                {"muid": f"User '{muid}' is not a member of this company's organisation."}
            )

        # ── Prevent duplicate active nominations ─────────────────────────────
        existing = UserMentor.objects.filter(
            user=user,
            mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR,
            org=org,
        ).exclude(status=UserMentor.Status.REJECTED).first()
        if existing:
            raise serializers.ValidationError(
                f"This user already has a {existing.status} Company Mentor nomination for your company."
            )

        data["_user"] = user
        data["_org"] = org
        return data

    def save(self):
        nominator_id = self.context.get("user_id")
        user = self.validated_data["_user"]
        reason = self.validated_data.get("reason", "")
        org = self.validated_data["_org"]

        from utils.utils import DateTimeUtils
        current_time = DateTimeUtils.get_current_utc_time()

        mentor = UserMentor.objects.create(
            id=str(uuid.uuid4()),
            user=user,
            mentor_tier=UserMentor.MentorTier.COMPANY_MENTOR,
            org=org,
            reason=reason,
            status=UserMentor.Status.APPROVED,
            verified_at=current_time,  
            created_by_id=nominator_id,
            updated_by_id=nominator_id,
            created_at=current_time,
            updated_at=current_time,
        )
        return mentor



class CompanyMentorListSerializer(serializers.ModelSerializer):
    """Serializer for listing Company Mentor nominations."""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    org_name = serializers.CharField(source="org.title", read_only=True, default=None)

    class Meta:
        model = UserMentor
        fields = [
            "id",
            "user_id",
            "user_name",
            "user_email",
            "org_name",
            "mentor_tier",
            "status",
            "reason",
            "verification_note",
            "verified_at",
        ]
