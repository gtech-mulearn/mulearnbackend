import uuid
from rest_framework import serializers
from django.db import transaction
from django.utils.text import slugify

from db.company import Company, CompanyAdminLink
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
    # PRD §15 — verification evidence is required at registration, not optional
    # metadata; the model field itself allows null/blank so this must be
    # overridden here to actually enforce it.
    verification_document_url = serializers.URLField(required=True)

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
            "verification_document_url",
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
            "verification_document_url",
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

        # Regenerate a unique slug when the name changes
        if rename:
            base_slug = slugify(new_name)
            slug = base_slug
            counter = 1
            while Company.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            validated_data['slug'] = slug  # inject so setattr picks it up

        update_fields = list(validated_data.keys())

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        with transaction.atomic():
            instance.save(update_fields=update_fields)

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
    profile_completeness = serializers.SerializerMethodField()
    verification_sla_message = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = "__all__"

    # PRD §4.3 — profile completeness scoring, shown to both the company (as
    # a nudge) and to admin (as a signal of how genuine/complete an
    # application is before verifying). Weighted equally across a fixed set
    # of "worth filling in" fields rather than every column, so a bare-bones
    # required-fields-only registration doesn't already read as 100%.
    COMPLETENESS_FIELDS = [
        "logo", "description", "short_pitch", "industry_sector", "website_link",
        "location", "legal_name", "registration_number", "company_size",
        "linkedin_url", "verification_document_url", "founded_year",
        "remote_policy", "culture_text", "tech_stack", "perks", "testimonials", "gallery",
    ]

    def get_profile_completeness(self, obj):
        filled = sum(1 for f in self.COMPLETENESS_FIELDS if getattr(obj, f, None))
        return round((filled / len(self.COMPLETENESS_FIELDS)) * 100)

    def get_verification_sla_message(self, obj):
        if obj.status == "pending":
            return "Registrations are typically reviewed within 3 business days."
        return None

class CompanyVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["verified", "rejected"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("status") == "rejected" and not data.get("rejection_reason"):
            raise serializers.ValidationError("Rejection reason is required when rejecting.")
        if data.get("status") == "verified" and not (self.instance and self.instance.verification_document_url):
            raise serializers.ValidationError(
                "This company has not submitted a verification document and cannot be verified."
            )
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
    verified_since = serializers.DateTimeField(source='verified_at', read_only=True, default=None)
    collaboration_summary = serializers.SerializerMethodField()
    impact_summary = serializers.SerializerMethodField()

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
            "gallery",
            "verified_since",
            "collaboration_summary",
            "impact_summary",
        ]

    def get_collaboration_summary(self, obj):
        """
        PRD §10.3 — collaboration history as a trust signal on the public
        profile ("partnered with 12 campuses"). Only counts ACCEPTED
        collaborations; open/pending/declined/withdrawn are not a company's
        earned trust signal.
        """
        from db.company import Collaboration
        accepted = Collaboration.objects.filter(company=obj, status=Collaboration.Status.ACCEPTED)
        return {
            "total_partnerships": accepted.count(),
            "campus_partnerships": accepted.filter(target_type=Collaboration.TargetType.CAMPUS).count(),
            "ig_partnerships": accepted.filter(target_type=Collaboration.TargetType.IG).count(),
        }

    def get_impact_summary(self, obj):
        """
        PRD §13.3 — optional summarized impact report on the public profile,
        gated on the company's own opt-in (`publish_impact_report`) so a
        company controls whether this becomes a public marketing signal.
        """
        if not getattr(obj, "publish_impact_report", False):
            return None
        from api.dashboard.company.feedback_views import build_impact_summary
        return build_impact_summary(obj)


# ---------------------------------------------------------------------------
# Company Mentor serializers
# ---------------------------------------------------------------------------

from db.user import User as _User, UserMentor, MentorApplication


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

        # ── Conflict-of-interest: cannot nominate yourself ───────────────────
        if user.id == self.context.get("user_id"):
            raise serializers.ValidationError(
                {"muid": "You cannot nominate yourself as a mentor."}
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
        existing_pending = MentorApplication.objects.filter(
            user=user, tier=UserMentor.MentorTier.COMPANY_MENTOR, org=org,
            status=MentorApplication.Status.PENDING,
        ).exists()
        already_granted = MentorScopeGrant.objects.filter(
            mentor__user=user, scope_type=MentorScopeGrant.ScopeType.COMPANY_MENTOR,
            scope_id=str(org.id), is_active=True,
        ).exists()
        if existing_pending or already_granted:
            raise serializers.ValidationError(
                f"This user already has an active or pending Company Mentor nomination for your company."
            )

        data["_user"] = user
        data["_org"] = org
        return data

    def save(self):
        from api.dashboard.mentor.serializers import _apply_application_approval

        nominator_id = self.context.get("user_id")
        user = self.validated_data["_user"]
        reason = self.validated_data.get("reason", "")
        org = self.validated_data["_org"]

        current_time = DateTimeUtils.get_current_utc_time()

        with transaction.atomic():
            # Nomination IS approval (§4.2) — create the application already
            # APPROVED and apply the shared approval side-effects (profile
            # upsert, grant, role, org link) in one step.
            application = MentorApplication.objects.create(
                user=user,
                tier=UserMentor.MentorTier.COMPANY_MENTOR,
                org=org,
                reason=reason,
                source=MentorApplication.SourceType.OWNER_NOMINATED,
                status=MentorApplication.Status.APPROVED,
                nominated_by_id=nominator_id,
                verified_by_id=nominator_id,
                verified_at=current_time,
                created_by_id=nominator_id,
                updated_by_id=nominator_id,
                created_at=current_time,
                updated_at=current_time,
            )
            grant = _apply_application_approval(application, nominator_id)
            if grant:
                application.resulting_grant = grant
                application.save(update_fields=["resulting_grant"])

        return application


class CompanyMentorApplySerializer(serializers.Serializer):
    """
    Self-onboarding: a user applies to become a specific company's mentor
    themselves (PRD §4.2), distinct from CompanyMentorNominateAPI's
    owner-initiated path. Sits PENDING until the company owner reviews it —
    the applicant does not receive the tier until the owner acts.
    """
    company_id = serializers.CharField(help_text="ID of the Company to apply to.")
    about = serializers.CharField(required=False, allow_blank=True)
    expertise = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    hours = serializers.IntegerField(required=False, min_value=0, default=0)

    def validate(self, data):
        user_id = self.context["user_id"]
        company = Company.objects.filter(id=data["company_id"], status="verified").first()
        if not company:
            raise serializers.ValidationError({"company_id": "Verified company not found."})

        # Conflict-of-interest: the owner (or an accepted co-admin, who already
        # holds equivalent authority) reviewing their own mentor application
        # would be self-approval by construction — block it at apply time.
        from api.dashboard.company.company_views import is_company_owner_or_admin
        if is_company_owner_or_admin(user_id, company):
            raise serializers.ValidationError(
                {"company_id": "You cannot apply to be a mentor for a company you own or co-administer."}
            )

        org = company.org
        if not org:
            raise serializers.ValidationError("Company organization record not found.")

        if MentorApplication.objects.filter(
            user_id=user_id, tier=UserMentor.MentorTier.COMPANY_MENTOR, org=org,
            status=MentorApplication.Status.PENDING,
        ).exists():
            raise serializers.ValidationError("You already have a pending application for this company.")

        if MentorScopeGrant.objects.filter(
            mentor__user_id=user_id, scope_type=MentorScopeGrant.ScopeType.COMPANY_MENTOR,
            scope_id=str(org.id), is_active=True,
        ).exists():
            raise serializers.ValidationError("You are already an approved mentor for this company.")

        data["_company"] = company
        data["_org"] = org
        return data

    def save(self):
        import uuid as _uuid
        from datetime import timedelta

        user_id = self.context["user_id"]
        company = self.validated_data["_company"]
        org = self.validated_data["_org"]
        now = DateTimeUtils.get_current_utc_time()

        application = MentorApplication.objects.create(
            user_id=user_id,
            tier=UserMentor.MentorTier.COMPANY_MENTOR,
            org=org,
            about=self.validated_data.get("about"),
            expertise=self.validated_data.get("expertise"),
            reason=self.validated_data.get("reason"),
            hours=self.validated_data.get("hours", 0),
            source=MentorApplication.SourceType.SELF_APPLIED,
            status=MentorApplication.Status.PENDING,
            nomination_expires_at=now + timedelta(days=14),
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        try:
            from api.notification.notifications_utils import NotificationUtils
            from django.conf import settings
            from db.user import User
            applicant = User.every.filter(id=user_id).first()
            NotificationUtils.insert_notification(
                user=company.company_user,
                title="New Company Mentor Application",
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
        fields = [
            "id",
            "user_id",
            "user_name",
            "user_email",
            "org_name",
            "tier",
            "source",
            "status",
            "reason",
            "verification_note",
            "verified_at",
        ]


class CompanyAdminLinkSerializer(serializers.ModelSerializer):
    """Addon §6.5 — full history of co-admin invites/acceptances/revocations for a company."""

    user_muid = serializers.CharField(source="user.muid", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    invited_by_name = serializers.CharField(source="invited_by.full_name", read_only=True, default=None)
    revoked_by_name = serializers.CharField(source="revoked_by.full_name", read_only=True, default=None)

    class Meta:
        model = CompanyAdminLink
        fields = [
            "id",
            "user_muid",
            "user_name",
            "status",
            "invited_by_name",
            "invited_at",
            "responded_at",
            "revoked_by_name",
            "revoked_at",
        ]
