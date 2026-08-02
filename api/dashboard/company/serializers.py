import uuid
from rest_framework import serializers
from django.db import transaction
from django.utils.text import slugify

from db.company import Company
from db.organization import Organization, District, State, Country
from db.user import UserRoleLink, Role
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils
from django.db import transaction
from db.user import MentorScopeGrant
from db.organization import UserOrganizationLink

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

from db.user import MentorApplication, User as _User, UserMentor
from db.mentor import SystemActionLog


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
        nominator_id = self.context.get("user_id")
        muid = data.get("muid")

        # ── Resolve muid → User ──────────────────────────────────────────────
        user = _User.objects.filter(muid=muid).first()
        if not user:
            raise serializers.ValidationError(
                {"muid": f"No platform user found with muid '{muid}'."}
            )

        if str(user.id) == str(nominator_id):
            raise serializers.ValidationError(
                {"muid": "You cannot nominate yourself as your company's mentor."}
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
        existing = MentorApplication.objects.filter(
            user=user,
            mentor_tier=MentorApplication.MentorTier.COMPANY_MENTOR,
            org=org,
        ).exclude(status__in=[
            MentorApplication.Status.REJECTED,
            MentorApplication.Status.GRANT_REVOKED
        ]).first()
        if existing:
            raise serializers.ValidationError(
                f"This user already has a {existing.status.lower()} Company Mentor application for your company."
            )

        data["_user"] = user
        data["_org"] = org
        return data

    def save(self):
        nominator_id = self.context.get("user_id")
        user = self.validated_data["_user"]
        reason = self.validated_data.get("reason", "")
        org = self.validated_data["_org"]

        current_time = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            # 1. Create or update UserMentor profile (can be empty)
            UserMentor.objects.get_or_create(
                user=user,
                defaults={
                    "created_by_id": nominator_id,
                    "updated_by_id": nominator_id,
                }
            )

            # 2️⃣ Create an approved MentorApplication record
            application = MentorApplication.objects.create(
                user=user,
                mentor_tier=MentorApplication.MentorTier.COMPANY_MENTOR,
                org=org,
                reason=reason,
                status=MentorApplication.Status.APPROVED,
                verified_by_id=nominator_id,
                verified_at=current_time,
                created_by_id=nominator_id,
                updated_by_id=nominator_id,
                created_at=current_time,
                updated_at=current_time,
            )

            # 2️⃣ Grant the MENTOR role
            mentor_role = Role.objects.filter(title=RoleType.MENTOR.value).first()
            if not mentor_role:
                raise serializers.ValidationError("MENTOR role not found in database.")

            UserRoleLink.objects.get_or_create(
                user=user,
                role=mentor_role,
                defaults={
                    "verified": True,
                    "created_by_id": nominator_id,
                    "created_at": current_time,
                },
            )

            # 3️⃣ Create MentorScopeGrant
            MentorScopeGrant.objects.create(
                application=application,
                scope_type=MentorApplication.MentorTier.COMPANY_MENTOR,
                scope_id=str(org.id),
                is_active=True,
                granted_by_id=nominator_id,
                granted_at=current_time,
            )

            # 4️⃣ Ensure org link is verified
            # (link already exists — validated in validate() — just ensure verified=True)
            UserOrganizationLink.objects.filter(
                user=user, org=org
            ).update(verified=True)

        # Log the direct nomination action
        nominator = _User.objects.get(id=nominator_id)
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.MENTOR_VERIFY.value,
            actor_user=nominator,
            subject_user=user,
            entity_name='mentor_application',
            entity_id=application.id,
            new_data={
                'status': application.status,
                'mentor_tier': application.mentor_tier,
                'org_id': str(application.org.id) if application.org else None,
                'org_title': application.org.title if application.org else None,
                'reason': reason,
                'nomination': True
            },
            remarks=f"Company owner {nominator.full_name} directly nominated {user.full_name} as a mentor for {org.title}."
        )

        return application


class CompanyMentorApplySerializer(serializers.Serializer):
    """Self-onboarding: an authenticated user applies to become mentor for a
    specific company (identified by ``company_id``). Sits PENDING until the
    company owner reviews it via MentorVerifyAPI — unlike nomination, this
    does NOT auto-approve or grant anything immediately.
    """

    company_id = serializers.CharField(
        help_text="ID of the company to apply to as a mentor."
    )
    about = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    expertise = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    hours = serializers.IntegerField(required=False, allow_null=True, min_value=0)

    def validate(self, data):
        user_id = self.context.get("user_id")
        company_id = data.get("company_id")

        company = Company.objects.filter(id=company_id, status="verified").first()
        if not company:
            raise serializers.ValidationError(
                {"company_id": "No verified company found with this ID."}
            )

        if company.company_user_id == user_id:
            raise serializers.ValidationError(
                "You cannot apply to be a mentor for your own company."
            )

        org = company.org
        if not org:
            raise serializers.ValidationError(
                "Company organization record not found. Ensure the company is verified."
            )

        existing = MentorApplication.objects.filter(
            user_id=user_id,
            mentor_tier=MentorApplication.MentorTier.COMPANY_MENTOR,
            org=org,
        ).exclude(status__in=[
            MentorApplication.Status.REJECTED,
            MentorApplication.Status.GRANT_REVOKED
        ]).first()
        if existing:
            raise serializers.ValidationError(
                f"You already have a {existing.status.lower()} Company Mentor application for this company."
            )

        data["_company"] = company
        data["_org"] = org
        return data

    def save(self):
        user_id = self.context.get("user_id")
        company = self.validated_data["_company"]
        org = self.validated_data["_org"]
        about = self.validated_data.get("about")
        expertise = self.validated_data.get("expertise")
        reason = self.validated_data.get("reason", "")
        hours = self.validated_data.get("hours")

        now = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            profile, created = UserMentor.objects.get_or_create(
                user_id=user_id,
                defaults={
                    "about": about,
                    "expertise": expertise,
                    "hours": hours or 0,
                    "created_by_id": user_id,
                    "updated_by_id": user_id,
                },
            )
            if not created:
                if about is not None:
                    profile.about = about
                if expertise is not None:
                    profile.expertise = expertise
                if hours is not None:
                    profile.hours = hours
                profile.updated_by_id = user_id
                profile.updated_at = now
                profile.save()

            application = MentorApplication.objects.create(
                user_id=user_id,
                mentor_tier=MentorApplication.MentorTier.COMPANY_MENTOR,
                org=org,
                reason=reason,
                status=MentorApplication.Status.PENDING,
                created_by_id=user_id,
                updated_by_id=user_id,
                created_at=now,
                updated_at=now,
            )

        try:
            from api.notification.notifications_utils import NotificationUtils
            from django.conf import settings

            applicant = _User.objects.get(id=user_id)
            NotificationUtils.insert_notification(
                user=company.company_user,
                title="New Mentor Application",
                description=f"{applicant.full_name} has applied to be a mentor for your company.",
                button="View Application",
                url=f"{settings.FR_DOMAIN_NAME}/dashboard/company/mentor/list/",
                created_by=applicant,
            )
        except Exception:
            pass

        return application


class CompanyMentorListSerializer(serializers.ModelSerializer):
    """Serializer for listing Company Mentor nominations/applications."""

    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)
    org_name = serializers.CharField(source="org.title", read_only=True, default=None)

    class Meta:
        model = MentorApplication
        model = MentorApplication
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
