import uuid
from datetime import timedelta
from rest_framework import serializers
import re
from db.user import Socials, UserMentor, UserRoleLink, Role, MentorScopeGrant, MentorApplication, UserSettings, User


class MentorScopeGrantSerializer(serializers.ModelSerializer):
    granted_by_name = serializers.CharField(source='granted_by.full_name', read_only=True)
    revoked_by_name = serializers.CharField(source='revoked_by.full_name', read_only=True, default=None)

    class Meta:
        model = MentorScopeGrant
        fields = [
            "id",
            "scope_type",
            "scope_id",
            "is_active",
            "granted_by_name",
            "granted_at",
            "revoked_by_name",
            "revoked_at",
        ]


class PersonaStatusSerializer(serializers.Serializer):
    active_persona = serializers.CharField()
    active_scope_type = serializers.CharField(allow_null=True)
    active_scope_id = serializers.CharField(allow_null=True)
    active_scope_name = serializers.CharField(allow_null=True)


class PersonaSwitchSerializer(serializers.Serializer):
    persona = serializers.ChoiceField(choices=UserSettings.PersonaType.choices)
    # Optional: when persona == "mentor" and the caller holds more than one
    # active scope grant, these pick which one to switch into. If omitted,
    # falls back to the most-recently-granted scope (previous behavior).
    scope_type = serializers.CharField(required=False, allow_null=True)
    scope_id = serializers.CharField(required=False, allow_null=True)

from db.task import InterestGroup, UserIgLink
from utils.types import RoleType, OrganizationType
from utils.utils import DateTimeUtils, get_user_mentor_profile
from django.db import transaction
from django.db.models import Q
from db.organization import Organization

class MentorRegisterSerializer(serializers.ModelSerializer):
    # Plain (not SerializerMethodField) so these are actually accepted as
    # input on create — a SerializerMethodField is read-only and silently
    # drops any about/expertise/hours sent in the request body. Neither is a
    # field on MentorApplication itself (they live on the UserMentor
    # profile); to_representation below fills them in for GET responses.
    # write_only: MentorApplication has no such attributes, so the default
    # to_representation() read path would raise AttributeError trying to
    # access instance.about/.expertise/.hours. to_representation() below
    # fills the read side in manually from the UserMentor profile instead.
    about = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    expertise = serializers.CharField(required=False, allow_blank=True, allow_null=True, write_only=True)
    hours = serializers.IntegerField(required=False, allow_null=True, min_value=0, write_only=True)

    linkedin = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=255)
    mentor_tier = serializers.ChoiceField(choices=[
        MentorApplication.MentorTier.IG_MENTOR.value,
        MentorApplication.MentorTier.COMPANY_MENTOR.value,
        MentorApplication.MentorTier.CAMPUS_MENTOR.value,
    ])
    org = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(
            org_type__in=[OrganizationType.COMPANY.value, OrganizationType.COLLEGE.value]
        ),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MentorApplication
        fields = [
            "id",
            "about",
            "expertise",
            "hours",
            "reason",
            "preferred_ig_ids",
            "linkedin",
            "mentor_tier",
            "org",
        ]

    def to_representation(self, instance):
        # about/expertise/hours aren't fields on MentorApplication — pull the
        # current values from the linked UserMentor profile for output.
        data = super().to_representation(instance)
        user_mentor = get_user_mentor_profile(instance.user_id)
        data["about"] = user_mentor.about if user_mentor else None
        data["expertise"] = user_mentor.expertise if user_mentor else None
        data["hours"] = user_mentor.hours if user_mentor else None
        return data

    def validate_preferred_ig_ids(self, value):
        if not value or not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("At least one preferred IG ID must be provided.")
        for ig_id in value:
            if not InterestGroup.objects.filter(id=ig_id).exists():
                raise serializers.ValidationError(f"Invalid IG ID: {ig_id}")
        return value

    def validate_linkedin(self, value):
        if value:
            linkedin_pattern = r'^(https?://)?(www\.)?linkedin\.com/in/[\w\d\-._~:/?#\[\]@!$&\'()*+,;=]+/?$'
            if not re.match(linkedin_pattern, value):
                raise serializers.ValidationError("Invalid LinkedIn profile URL format. It should be like https://www.linkedin.com/in/your-profile-name.")
        return value

    def validate(self, attrs):
        mentor_tier = attrs.get('mentor_tier')
        org = attrs.get('org')

        if mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR.value:
            if not org:
                raise serializers.ValidationError({'org': 'Organization is required for a Company Mentor application.'})
            if org.org_type != OrganizationType.COMPANY.value:
                raise serializers.ValidationError({'org': 'A valid company organization is required.'})
        elif mentor_tier == MentorApplication.MentorTier.CAMPUS_MENTOR.value:
            if not org:
                raise serializers.ValidationError({'org': 'Organization is required for a Campus Mentor application.'})
            if org.org_type != OrganizationType.COLLEGE.value:
                raise serializers.ValidationError({'org': 'A valid college organization is required.'})
        elif mentor_tier == MentorApplication.MentorTier.IG_MENTOR.value:
            # For IG_MENTOR, an organization is optional and not used for scope.
            # It is stored for metadata purposes if provided.
            pass
        return attrs

    def create(self, validated_data):
        user_id = self.context["user_id"]
        linkedin_url = validated_data.pop('linkedin', None)
        now = DateTimeUtils.get_current_utc_time()
        # Separate profile data from application data
        profile_data = {
            "about": validated_data.pop("about", None),
            "expertise": validated_data.pop("expertise", None),
            "hours": validated_data.pop("hours", None),
        }

        with transaction.atomic():
            # Save linkedin url directly to socials table
            if linkedin_url:
                socials, _ = Socials.objects.get_or_create(
                    user_id=user_id,
                    defaults={'created_by_id': user_id, 'updated_by_id': user_id}
                )
                socials.linkedin = linkedin_url
                socials.updated_by_id = user_id
                socials.save(update_fields=['linkedin', 'updated_by_id'])

            # 1. Create or update the single UserMentor profile
            mentor_profile, created = UserMentor.objects.get_or_create(
                user_id=user_id,
                defaults={
                    "about": profile_data["about"],
                    "expertise": profile_data["expertise"],
                    "hours": profile_data["hours"],
                    "created_by_id": user_id,
                    "updated_by_id": user_id,
                }
            )
            if not created:
                for attr, value in profile_data.items():
                    if value is not None:
                        setattr(mentor_profile, attr, value)
                mentor_profile.updated_by_id = user_id
                mentor_profile.updated_at = now
                mentor_profile.save()

            # 2. Create the new MentorApplication record
            application = MentorApplication.objects.create(
                user_id=user_id,
                status=MentorApplication.Status.PENDING,
                created_by_id=user_id,
                updated_by_id=user_id,
                created_at=now,
                updated_at=now,
                **validated_data
            )

        try:
            from api.notification.notifications_utils import NotificationUtils
            from db.user import User, UserRoleLink
            from utils.types import RoleType
            from db.company import Company
            from db.mentor import SystemActionLog
            from django.conf import settings

            requester = User.every.filter(id=user_id).first()

            mentor_tier = validated_data.get('mentor_tier')
            org = validated_data.get('org') # This is the application's org

            if mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR.value:
                try:
                    company = Company.objects.get(org=org, status="verified")
                    NotificationUtils.insert_notification(
                        user=company.company_user,
                        title="New Mentor Application",
                        description=f"{requester.full_name} has applied to be a mentor for your company.",
                        button="View Application",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/company/mentor/list/",
                        created_by=requester,
                    )
                except Company.DoesNotExist:
                    pass

                # Log for admins instead of notifying them
                SystemActionLog.objects.create(
                    action_type=SystemActionLog.ActionType.MENTOR_APP_SUBMITTED.value,
                    actor_user=requester,
                    subject_user=requester,
                    entity_name='mentor_application',
                    entity_id=application.id,
                    new_data={
                        'mentor_tier': application.mentor_tier,
                        'org_id': str(application.org.id) if application.org else None,
                        'org_title': application.org.title if application.org else None,
                        'reason': application.reason,
                        'preferred_ig_ids': application.preferred_ig_ids,
                    },
                    remarks=f"New company mentor application from {requester.full_name} for {org.title}."
                )

            else: # For CAMPUS_MENTOR and IG_MENTOR, notify admins
                tier_display = "Campus" if mentor_tier == MentorApplication.MentorTier.CAMPUS_MENTOR.value else "IG"
                org_display = f" for {org.title}" if org else ""
                admin_roles = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
                for admin_link in admin_roles:
                    NotificationUtils.insert_notification(
                        user=admin_link.user,
                        title=f"New {tier_display} Mentor Application",
                        description=f"{requester.full_name} has applied to be a {tier_display.lower()} mentor{org_display}.",
                        button="View Application",
                        url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/applications/",
                        created_by=requester,
                    )

                if mentor_tier == MentorApplication.MentorTier.IG_MENTOR.value and application.preferred_ig_ids:
                    from db.task import InterestGroup
                    from .dash_mentor_helper import notify_ig_leads
                    igs = InterestGroup.objects.filter(id__in=application.preferred_ig_ids)
                    for ig in igs:
                        notify_ig_leads(ig, requester, application)
        except Exception:
            # Don't let a notification failure block the application itself,
            # but do log it — a swallowed exception here previously left no
            # trace of a failed admin/IG-lead notification.
            import logging
            logging.getLogger(__name__).exception(
                "Failed to notify/log new mentor application %s", application.id
            )

        return application

class MentorUpdateSerializer(serializers.ModelSerializer):
    # write_only: MentorApplication has no such attributes — see the same
    # note on MentorRegisterSerializer above. to_representation() below
    # fills the read side in from the UserMentor profile instead.
    about = serializers.CharField(required=False, allow_blank=True, write_only=True)
    expertise = serializers.CharField(required=False, allow_blank=True, write_only=True)
    hours = serializers.IntegerField(required=False, write_only=True)

    linkedin = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=255)
    mentor_tier = serializers.ChoiceField(choices=[
        MentorApplication.MentorTier.IG_MENTOR.value,
        MentorApplication.MentorTier.COMPANY_MENTOR.value,
        MentorApplication.MentorTier.CAMPUS_MENTOR.value,
    ], required=False)
    org = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.filter(
            org_type__in=[OrganizationType.COMPANY.value, OrganizationType.COLLEGE.value]
        ),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MentorApplication
        fields = [
            "id",
            "about",
            "expertise",
            "hours",
            "reason",
            "preferred_ig_ids",
            "linkedin",
            "mentor_tier",
            "org",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user_mentor = get_user_mentor_profile(instance.user_id)
        data["about"] = user_mentor.about if user_mentor else None
        data["expertise"] = user_mentor.expertise if user_mentor else None
        data["hours"] = user_mentor.hours if user_mentor else None
        return data

    def validate_preferred_ig_ids(self, value):
        if value:
            if not isinstance(value, list) or len(value) == 0:
                raise serializers.ValidationError("At least one preferred IG ID must be provided.")
            for ig_id in value:
                if not InterestGroup.objects.filter(id=ig_id).exists():
                    raise serializers.ValidationError(f"Invalid IG ID: {ig_id}")
        return value

    def validate_linkedin(self, value):
        if value:
            linkedin_pattern = r'^(https?://)?(www\.)?linkedin\.com/in/[\w\d\-._~:/?#\[\]@!$&\'()*+,;=]+/?$'
            if not re.match(linkedin_pattern, value):
                raise serializers.ValidationError("Invalid LinkedIn profile URL format. It should be like https://www.linkedin.com/in/your-profile-name.")
        return value

    def validate(self, attrs):
        # Every mentor must mentor at least one Interest Group (regardless of
        # tier or any org scope) — the IG list cannot be cleared to empty.
        instance = self.instance
        if instance and "preferred_ig_ids" in attrs and not attrs["preferred_ig_ids"]:
            raise serializers.ValidationError(
                {"preferred_ig_ids": "You must mentor at least one Interest Group."}
            )

        # If neither is in payload, nothing to validate
        if 'mentor_tier' not in attrs and 'org' not in attrs:
            return attrs

        mentor_tier = attrs.get('mentor_tier', instance.mentor_tier if instance else None)
        
        # Handle case where 'org' is explicitly passed as null
        if 'org' in attrs and attrs['org'] is None:
            org = None
        else:
            org = attrs.get('org', instance.org if instance else None)

        # Prevent duplicate PENDING or APPROVED applications on update.
        if instance:
            qs = MentorApplication.objects.filter(
                user=instance.user,
                mentor_tier=mentor_tier,
                status__in=[MentorApplication.Status.PENDING, MentorApplication.Status.APPROVED]
            ).exclude(pk=instance.id)

            if mentor_tier == MentorApplication.MentorTier.IG_MENTOR.value:
                if qs.exists():
                    raise serializers.ValidationError(
                        "You already have an active or pending IG mentor application."
                    )
            elif mentor_tier in [MentorApplication.MentorTier.COMPANY_MENTOR.value, MentorApplication.MentorTier.CAMPUS_MENTOR.value]:
                qs = qs.filter(org=org)
                if qs.exists():
                    tier_name = str(mentor_tier).replace('_', ' ').title()
                    raise serializers.ValidationError(
                        f"You already have an active or pending {tier_name} application for this organization."
                    )

        if mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR.value:
            if not org:
                raise serializers.ValidationError({'org': 'Organization is required for a Company Mentor application.'})
            if org.org_type != OrganizationType.COMPANY.value:
                raise serializers.ValidationError({'org': 'A valid company organization is required.'})
        elif mentor_tier == MentorApplication.MentorTier.CAMPUS_MENTOR.value:
            if not org:
                raise serializers.ValidationError({'org': 'Organization is required for a Campus Mentor application.'})
            if org.org_type != OrganizationType.COLLEGE.value:
                raise serializers.ValidationError({'org': 'A valid college organization is required.'})
        # For IG_MENTOR, an organization is optional, so no specific validation is needed.
        return attrs

    def update(self, instance, validated_data):
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_by_id'] = self.context.get("user_id", instance.user_id)

        validated_data.pop('linkedin', None)

        # Update profile details on the central UserMentor record
        profile_data = {
            "about": validated_data.pop("about", None),
            "expertise": validated_data.pop("expertise", None),
            "hours": validated_data.pop("hours", None),
        }
        
        mentor_profile = UserMentor.objects.filter(user=instance.user).first()
        if mentor_profile:
            for attr, value in profile_data.items():
                if value is not None:
                    setattr(mentor_profile, attr, value)
            mentor_profile.save()

        # Application-specific fields cannot be changed on an approved application
        if instance.status == MentorApplication.Status.APPROVED:
            validated_data.pop('org', None)
            validated_data.pop('mentor_tier', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class MentorApplicationListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)

    class Meta:
        model = MentorApplication
        fields = [
            "id",
            "user_id",
            "user_full_name",
            "user_email",
            "muid",
            "reason",
            "preferred_ig_ids",
            "verification_note",
            "verified_at",
            "mentor_tier",
            "org",
            "status",
            "created_at",
            "updated_at"
        ]

class MentorDetailSerializer(serializers.ModelSerializer):
    """
    This serializer is now for the central UserMentor profile.
    It shows the core profile and lists all associated applications.
    """
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    applications = MentorApplicationListSerializer(many=True, read_only=True, source='user.mentor_applications')
    avg_rating = serializers.SerializerMethodField()
    rating_count = serializers.SerializerMethodField()

    class Meta:
        model = UserMentor
        fields = [
            "id",
            "user_full_name",
            "muid",
            "about",
            "expertise",
            "hours",
            "applications",
            "avg_rating",
            "rating_count",
            "created_at",
            "updated_at",
        ]

    def _rating_aggregate(self, obj):
        cached = getattr(obj, '_rating_aggregate_cache', None)
        if cached is not None:
            return cached
        from django.db.models import Avg, Count
        from db.mentor import MentorshipSessionUserLink, MentorshipSession

        # Ratings are recorded on the MENTEE's own participant link (a mentee
        # rates the mentor of the session they attended — see
        # MentorshipSessionUserLink.rating), not on the mentor's own link. So
        # first resolve which sessions this mentor ran, then aggregate the
        # mentee-side ratings for those sessions.
        mentor_session_ids = list(MentorshipSessionUserLink.objects.filter(
            user_id=obj.user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
        ).values_list('session_id', flat=True))

        session_stats = MentorshipSessionUserLink.objects.filter(
            session_id__in=mentor_session_ids,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
            rating__isnull=False,
        ).aggregate(avg=Avg('rating'), count=Count('id'))

        # PRD §9.2/§9.3 — roll the company-facing structured feedback
        # (PRD §13, CompanyFeedback) tied to this mentor's own COMPANY_MENTOR
        # sessions into the same quality-score average shown on their
        # profile, so mentor quality isn't split across two invisible pools.
        from db.company import CompanyFeedback
        company_session_ids = list(MentorshipSessionUserLink.objects.filter(
            user_id=obj.user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            session__session_type=MentorshipSession.SessionType.COMPANY_SESSION,
        ).values_list('session_id', flat=True))
        company_stats = CompanyFeedback.objects.filter(
            interaction_type=CompanyFeedback.InteractionType.SESSION,
            entity_id__in=company_session_ids,
        ).aggregate(avg=Avg('rating'), count=Count('id'))

        total_count = (session_stats['count'] or 0) + (company_stats['count'] or 0)
        if not total_count:
            cached = {'avg_rating': None, 'rating_count': 0}
        else:
            weighted = (session_stats['avg'] or 0) * (session_stats['count'] or 0) + \
                       (company_stats['avg'] or 0) * (company_stats['count'] or 0)
            cached = {'avg_rating': weighted / total_count, 'rating_count': total_count}
        obj._rating_aggregate_cache = cached
        return cached

    def get_avg_rating(self, obj):
        return self._rating_aggregate(obj)['avg_rating']

    def get_rating_count(self, obj):
        return self._rating_aggregate(obj)['rating_count']

class MentorProfileUpdateSerializer(serializers.ModelSerializer):
    linkedin = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=255)

    class Meta:
        model = UserMentor
        fields = [
            "about",
            "expertise",
            "hours",
            "linkedin",
        ]

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.updated_by_id = user_id
        
        # linkedin is not on the model, it's handled in the view
        validated_data.pop('linkedin', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance

class MentorVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[MentorApplication.Status.APPROVED, MentorApplication.Status.REJECTED])
    verification_note = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if attrs.get("status") == MentorApplication.Status.REJECTED and not attrs.get("verification_note"):
            raise serializers.ValidationError("Verification note is required when rejecting.")
        return attrs

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        status = validated_data.get("status")
        now = DateTimeUtils.get_current_utc_time()
        
        instance.status = status
        instance.updated_by_id = user_id
        instance.updated_at = now
        
        if status == MentorApplication.Status.APPROVED:
            # Conflict-of-interest guard (addon §6.7): a user shouldn't hold
            # COMPANY_MENTOR scope for a company while their UserJobApplication
            # to that same company is still open.
            if instance.mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR and instance.org_id:
                from db.job import UserJobApplication
                has_open_application = UserJobApplication.objects.filter(
                    user_id=instance.user_id,
                    job__company__org_id=instance.org_id,
                    status__in=['Pending', 'In-Review', 'Shortlisted', 'Interview'],
                ).exists()
                if has_open_application:
                    raise serializers.ValidationError(
                        "This user has an open job application to this company and cannot be "
                        "granted Company Mentor status until that application is resolved."
                    )

            with transaction.atomic():
                instance.verified_by_id = user_id
                instance.verified_at = now

                # Revoke other approved applications of the same tier to enforce a single active affiliation per tier.
                other_apps_to_revoke = MentorApplication.objects.filter(
                    user=instance.user,
                    mentor_tier=instance.mentor_tier,
                    status=MentorApplication.Status.APPROVED
                ).exclude(id=instance.id)

                for app_to_revoke in other_apps_to_revoke:
                    app_to_revoke.status = MentorApplication.Status.REJECTED
                    app_to_revoke.verification_note = f"Affiliation changed and this application was superseded on {now.strftime('%Y-%m-%d')}."
                    app_to_revoke.updated_by_id = user_id
                    app_to_revoke.updated_at = now
                    app_to_revoke.save(update_fields=["status", "verification_note", "updated_by_id", "updated_at"])

                    # Deactivate all grants associated with the revoked application
                    MentorScopeGrant.objects.filter(
                        application=app_to_revoke, is_active=True
                    ).update(
                        is_active=False,
                        revoked_by_id=user_id,
                        revoked_at=now,
                    )

                    # If the revoked application was an IG_MENTOR one, deactivate its UserIgLink assignments
                    if app_to_revoke.mentor_tier == MentorApplication.MentorTier.IG_MENTOR and app_to_revoke.preferred_ig_ids:
                        UserIgLink.objects.filter(
                            user=app_to_revoke.user,
                            ig_id__in=app_to_revoke.preferred_ig_ids,
                            assignment_type=UserIgLink.AssignmentType.MENTOR,
                            is_active=True
                        ).update(is_active=False, unassigned_at=now)

                # Grant the tier being approved.
                if instance.mentor_tier != MentorApplication.MentorTier.IG_MENTOR:
                    scope_id = str(instance.org_id) if instance.org_id else None
                    grant, grant_created = MentorScopeGrant.objects.get_or_create(
                        application=instance,
                        scope_type=instance.mentor_tier,
                        scope_id=scope_id,
                        defaults={
                            "is_active": True,
                            "granted_by_id": user_id,
                            "granted_at": now,
                        },
                    )
                    if not grant_created and not grant.is_active:
                        grant.is_active = True
                        grant.revoked_by = None
                        grant.revoked_at = None
                        grant.save(update_fields=["is_active", "revoked_by", "revoked_at"])

                # Assign global MENTOR role
                mentor_role = Role.objects.filter(title=RoleType.MENTOR.value).first()
                if mentor_role:
                    role_link, created = UserRoleLink.objects.get_or_create(
                        user=instance.user,
                        role=mentor_role,
                        defaults={
                            "verified": True,
                            "created_by_id": user_id,
                            "created_at": now,
                        },
                    )
                    if not created and not role_link.verified:
                        role_link.verified = True
                        role_link.save(update_fields=["verified"])

                # Auto-assign UserIgLink from preferred IGs for ANY tier
                if instance.preferred_ig_ids:
                    from .dash_mentor_helper import reconcile_mentor_ig_links, reconcile_mentor_ig_grants

                    reconcile_mentor_ig_links(
                        instance.user, instance.preferred_ig_ids, user_id
                    )
                    reconcile_mentor_ig_grants(
                        instance, user_id
                    )

                # Auto-link COMPANY_MENTOR to the company's Organization
                if instance.mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR and instance.org:
                    from db.organization import UserOrganizationLink
                    org_link, created = UserOrganizationLink.objects.get_or_create(
                        user=instance.user,
                        org=instance.org,
                        defaults={
                            "verified": True,
                            "created_by_id": user_id,
                            "created_at": now,
                        },
                    )
                    if not created and not org_link.verified:
                        org_link.verified = True
                        org_link.save(update_fields=["verified"])

        elif status == MentorApplication.Status.REJECTED:
            instance.verification_note = validated_data.get("verification_note")

        instance.save()

        # Log every verify decision for the admin audit trail (addon §6.3).
        from db.mentor import SystemActionLog
        from db.user import User
        actor = User.every.filter(id=user_id).first()
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.MENTOR_VERIFY.value,
            actor_user=actor,
            subject_user=instance.user,
            entity_name='mentor_application',
            entity_id=instance.id,
            new_data={
                'status': instance.status,
                'mentor_tier': instance.mentor_tier,
                'verification_note': instance.verification_note,
                'verified_at': str(instance.verified_at) if instance.verified_at else None,
            },
            remarks=f"{instance.mentor_tier} application for {instance.user.full_name} was {instance.status.lower()} by {actor.full_name}."
        )

        try:
            is_company_mentor = instance.mentor_tier == MentorApplication.MentorTier.COMPANY_MENTOR and instance.org_id

            if status == MentorApplication.Status.REJECTED:
                from api.notification.notifications_utils import NotificationUtils
                from django.conf import settings

                if is_company_mentor:
                    # Company owner is the sole verifier for this tier — admin
                    # gets passive notification-only visibility (§4.5).
                    from .dash_mentor_helper import notify_admins_company_mentor_decision
                    notify_admins_company_mentor_decision(actor, instance, "rejected")
                else:
                    # Notify every admin except the actor themselves (a no-op
                    # skip when the actor is an IG lead, not an admin) —
                    # gives admins passive visibility whether an admin or an
                    # IG lead made the call.
                    tier_name = "IG" if instance.mentor_tier == MentorApplication.MentorTier.IG_MENTOR else "Campus"
                    all_admins = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
                    for admin_link in all_admins:
                        if admin_link.user == actor:
                            continue
                        NotificationUtils.insert_notification(
                            user=admin_link.user,
                            title=f"{tier_name} Mentor Application Rejected",
                            description=f"{actor.full_name} has rejected the {tier_name.lower()} mentor application for {instance.user.full_name}.",
                            button="View Details",
                            url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/applications/{instance.id}/",
                            created_by=actor,
                        )
            elif status == MentorApplication.Status.APPROVED and is_company_mentor:
                from .dash_mentor_helper import notify_admins_company_mentor_decision
                notify_admins_company_mentor_decision(actor, instance, "approved")
            elif status == MentorApplication.Status.APPROVED and instance.mentor_tier == MentorApplication.MentorTier.IG_MENTOR:
                is_admin_actor = UserRoleLink.objects.filter(user=actor, role__title=RoleType.ADMIN.value, is_active=True).exists()
                if not is_admin_actor:
                    # Approved by an IG lead, not an admin — passive visibility.
                    from api.notification.notifications_utils import NotificationUtils
                    from django.conf import settings
                    all_admins = UserRoleLink.objects.filter(role__title=RoleType.ADMIN.value, is_active=True).select_related('user')
                    for admin_link in all_admins:
                        NotificationUtils.insert_notification(
                            user=admin_link.user,
                            title="IG Mentor Application Approved",
                            description=f"{actor.full_name} approved the IG mentor application for {instance.user.full_name}.",
                            button="View Details",
                            url=f"{settings.FR_DOMAIN_NAME}/dashboard/mentor/applications/{instance.id}/",
                            created_by=actor,
                        )
        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Failed to notify/log mentor-verify decision for application %s", instance.id
            )

        return instance

from db.mentor import MentorshipSession
from db.organization import Organization
from db.task import InterestGroup
from .session_recurrence_helper import generate_recurring_sessions

class SessionCreateSerializer(serializers.ModelSerializer):
    child_session_ids = serializers.SerializerMethodField()
    recurrence_truncated = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "entity_id",
            "session_type",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "max_participants",
            "is_recurring",
            "recurrence_type",
            "recurrence_interval",
            "recurrence_end_date",
            "child_session_ids",
            "recurrence_truncated",
        ]

    def get_child_session_ids(self, obj):
        if obj.is_recurring:
            if hasattr(obj, '_child_session_ids'):
                return obj._child_session_ids
            return list(
                MentorshipSession.objects.filter(
                    parent_session_id=obj.id,
                    is_deleted=False
                ).values_list('id', flat=True)
            )
        return []

    def get_recurrence_truncated(self, obj):
        """
        True when the recurrence series hit the MAX_RECURRENCE_COUNT cap
        (session_recurrence_helper.py) before reaching recurrence_end_date —
        i.e. some occurrences within the requested end date were not
        generated. Lets the caller surface this to the mentor instead of the
        series silently stopping early with no signal.
        """
        return getattr(obj, '_recurrence_truncated', False)

    def validate(self, attrs):
        user_id = self.context.get("user_id")
        session_type = attrs.get('session_type')
        entity_id = attrs.get('entity_id')

        # Validate that the mentor has the required scope to create this session.
        if not session_type or not entity_id:
            raise serializers.ValidationError({"detail": "session_type and entity_id are required."})

        from .dash_mentor_helper import has_scope
        from db.user import MentorScopeGrant

        scope_type_map = {
            MentorshipSession.SessionType.IG_SESSION: MentorScopeGrant.ScopeType.IG_MENTOR,
            MentorshipSession.SessionType.CAMPUS_SESSION: MentorScopeGrant.ScopeType.CAMPUS_MENTOR,
            MentorshipSession.SessionType.COMPANY_SESSION: MentorScopeGrant.ScopeType.COMPANY_MENTOR,
        }
        required_scope = scope_type_map.get(session_type)

        if not required_scope:
            raise serializers.ValidationError({"session_type": "Invalid session type provided."})

        # A global mentor can create any session. Otherwise, check for a specific grant.
        is_global_mentor = has_scope(user_id, MentorScopeGrant.ScopeType.MENTOR)
        has_specific_grant = has_scope(user_id, required_scope, entity_id)

        if not is_global_mentor and not has_specific_grant:
            entity_type_name = session_type.split('_')[0].lower()
            raise serializers.ValidationError(
                f"You do not have an active mentor grant for this {entity_type_name}."
            )

        if MentorshipSession.objects.filter(
            title=attrs.get('title'),
            starts_at=attrs.get('starts_at'),
            entity_id=attrs.get('entity_id'),
            created_by_id=user_id,
            is_deleted=False
        ).exists():
            raise serializers.ValidationError("A session with this exact title and start time already exists.")

        if attrs.get('starts_at') >= attrs.get('ends_at'):
            raise serializers.ValidationError("Session start time must be before end time.")

        # ── Mode / venue constraints ────────────────────────────────────────
        mode = attrs.get('mode')
        venue = attrs.get('venue') or ""
        meeting_link = attrs.get('meeting_link') or ""

        if mode == MentorshipSession.Mode.ONLINE:
            if venue.strip():
                raise serializers.ValidationError(
                    {"venue": "Venue must not be provided for an online session."}
                )
        elif mode == MentorshipSession.Mode.OFFLINE:
            if meeting_link.strip():
                raise serializers.ValidationError(
                    {"meeting_link": "Meeting link must not be provided for an offline session."}
                )
        elif mode == MentorshipSession.Mode.HYBRID:
            errors = {}
            if not venue.strip():
                errors["venue"] = "Venue is required for a hybrid session."
            if not meeting_link.strip():
                errors["meeting_link"] = "Meeting link is required for a hybrid session."
            if errors:
                raise serializers.ValidationError(errors)

        is_recurring = attrs.get('is_recurring', False)
        if is_recurring:
            errors = {}
            if not attrs.get('recurrence_type'):
                errors['recurrence_type'] = "recurrence_type is required when is_recurring is true."
            if not attrs.get('recurrence_interval') or attrs.get('recurrence_interval') < 1:
                errors['recurrence_interval'] = "recurrence_interval must be a positive integer when is_recurring is true."
            if not attrs.get('recurrence_end_date'):
                errors['recurrence_end_date'] = "recurrence_end_date is required when is_recurring is true."
            elif attrs.get('starts_at') and attrs.get('recurrence_end_date') <= attrs.get('starts_at').date():
                errors['recurrence_end_date'] = "recurrence_end_date must be after the session starts_at date."

            if errors:
                raise serializers.ValidationError(errors)
        else:
            attrs['recurrence_type'] = None
            attrs['recurrence_interval'] = None
            attrs['recurrence_end_date'] = None

        return attrs

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        now = DateTimeUtils.get_current_utc_time()

        # Approved mentors are pre-vetted, so their sessions go live immediately
        # (no per-session admin gate). Admins moderate reactively via cancel.
        # This serializer is shared by the mentor and campus create paths; both
        # are gated to approved mentors, so auto-approval is safe for both.
        # Parent + recurring children are a multi-write → wrap atomically so a
        # failure mid-series never leaves an orphan parent.
        with transaction.atomic():
            session = MentorshipSession.objects.create(
                status=MentorshipSession.Status.SCHEDULED,
                approved_by_id=user_id,
                approved_at=now,
                created_by_id=user_id,
                updated_by_id=user_id,
                **validated_data
            )

            # Register the creating mentor as the session's MENTOR participant
            # so session-completion, rating roll-ups, and hours-contributed
            # tracking (which key off this link) have a row to attach to.
            from db.mentor import MentorshipSessionUserLink
            MentorshipSessionUserLink.objects.get_or_create(
                session=session,
                user_id=user_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            )

            if session.is_recurring:
                child_sessions, was_truncated = generate_recurring_sessions(session)
                session._child_session_ids = [c.id for c in child_sessions]
                session._recurrence_truncated = was_truncated
            else:
                session._child_session_ids = []
                session._recurrence_truncated = False

        return session

class SessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        fields = [
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "max_participants"
        ]

    def validate(self, attrs):
        # Allow partial updates by fetching from instance if not in data
        starts_at = attrs.get('starts_at', self.instance.starts_at) if self.instance else attrs.get('starts_at')
        ends_at = attrs.get('ends_at', self.instance.ends_at) if self.instance else attrs.get('ends_at')

        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError("Session start time must be before end time.")

        # ── Mode / venue constraints (resolve from instance for partial PATCH) ──
        mode = attrs.get('mode', self.instance.mode if self.instance else None)
        venue = (attrs.get('venue') if 'venue' in attrs else (self.instance.venue if self.instance else None)) or ""
        meeting_link = (attrs.get('meeting_link') if 'meeting_link' in attrs else (self.instance.meeting_link if self.instance else None)) or ""

        # On a mode change we auto-clear the field that no longer applies rather
        # than rejecting stale data. Switching an online session to offline (or
        # vice-versa) would otherwise fail because the previous meeting_link /
        # venue is still stored on the row.
        if mode == MentorshipSession.Mode.ONLINE:
            attrs["venue"] = ""
        elif mode == MentorshipSession.Mode.OFFLINE:
            attrs["meeting_link"] = ""
        elif mode == MentorshipSession.Mode.HYBRID:
            errors = {}
            if not venue.strip():
                errors["venue"] = "Venue is required for a hybrid session."
            if not meeting_link.strip():
                errors["meeting_link"] = "Meeting link is required for a hybrid session."
            if errors:
                raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")

        # Editing no longer reverts a SCHEDULED session to PENDING_APPROVAL —
        # approved mentors edit their own live sessions without re-approval.
        instance.updated_by_id = user_id

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance

class SessionListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    entity_name = serializers.SerializerMethodField()
    parent_session_id = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "entity_id",
            "entity_name",
            "session_type",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "status",
            "created_by_id",
            "created_by_name",
            "created_at",
            "max_participants",
            "meeting_link",
            "venue",
            "is_recurring",
            "parent_session_id",
            "recurrence_type",
            "recurrence_interval",
            "recurrence_end_date"
        ]

    @staticmethod
    def build_entity_maps(sessions):
        """
        Resolve IG/Organization names for a page of sessions in two queries
        total instead of one query per row. List views should call this and
        pass the result as context={"ig_map": ..., "org_map": ...}.
        """
        ig_ids = {s.entity_id for s in sessions if s.session_type == MentorshipSession.SessionType.IG_SESSION and s.entity_id}
        org_ids = {
            s.entity_id for s in sessions
            if s.session_type in (MentorshipSession.SessionType.CAMPUS_SESSION, MentorshipSession.SessionType.COMPANY_SESSION)
            and s.entity_id
        }
        ig_map = InterestGroup.objects.filter(id__in=ig_ids).in_bulk() if ig_ids else {}
        org_map = Organization.objects.filter(id__in=org_ids).in_bulk() if org_ids else {}
        return ig_map, org_map

    def get_entity_name(self, obj):
        ig_map = self.context.get("ig_map")
        org_map = self.context.get("org_map")

        if obj.session_type == MentorshipSession.SessionType.IG_SESSION:
            if ig_map is not None:
                ig = ig_map.get(obj.entity_id)
                return ig.name if ig else None
            ig = InterestGroup.objects.filter(id=obj.entity_id).first()
            return ig.name if ig else None
        elif obj.session_type in (
            MentorshipSession.SessionType.CAMPUS_SESSION,
            MentorshipSession.SessionType.COMPANY_SESSION,
        ):
            if org_map is not None:
                org = org_map.get(obj.entity_id)
                return org.title if org else None
            org = Organization.objects.filter(id=obj.entity_id).first()
            return org.title if org else None
        return None

class SessionDetailSerializer(SessionListSerializer):
    # All fields are already exposed by the list serializer; detail is kept as a
    # distinct type for endpoint clarity / future divergence.
    pass

class AdminSessionVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        MentorshipSession.Status.SCHEDULED,
        MentorshipSession.Status.REJECTED,
        MentorshipSession.Status.CANCELLED,
    ])
    apply_to_series = serializers.BooleanField(default=False, required=False)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        status = validated_data.get("status")
        apply_to_series = validated_data.get("apply_to_series", False)

        now = DateTimeUtils.get_current_utc_time()
        # Capture the pre-update status so a series bulk-update only touches
        # siblings in the same source state (PENDING→approve/reject,
        # SCHEDULED→cancel) — the transition is validated in the view.
        source_status = instance.status

        with transaction.atomic():
            # 1. Update and save the targeted session instance (triggers cache signal once)
            instance.status = status
            instance.updated_by_id = user_id

            if status == MentorshipSession.Status.SCHEDULED:
                instance.approved_by_id = user_id
                instance.approved_at = now

            instance.save()

            # 2. Bulk update the rest of the series (same source state) if requested
            if apply_to_series:
                root_id = instance.parent_session_id or instance.id
                update_kwargs = {
                    "status": status,
                    "updated_by_id": user_id,
                    # .update() bypasses auto_now — set it explicitly so
                    # siblings' updated_at reflects this bulk change.
                    "updated_at": now,
                }
                if status == MentorshipSession.Status.SCHEDULED:
                    update_kwargs["approved_by_id"] = user_id
                    update_kwargs["approved_at"] = now

                MentorshipSession.objects.filter(
                    Q(id=root_id) | Q(parent_session_id=root_id),
                    status=source_status,
                    is_deleted=False
                ).exclude(id=instance.id).update(**update_kwargs)
                
        # Make sure apply_to_series is available for view layer formatting
        validated_data['apply_to_series'] = apply_to_series
        return instance

from db.mentor import MentorAvailabilitySlot

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source='ig.name', read_only=True)
    
    class Meta:
        model = MentorAvailabilitySlot
        fields = [
            "id",
            "mentor_user_id",
            "ig_id",
            "ig_name",
            "weekday",
            "start_time",
            "end_time",
            "timezone",
            "is_active",
            "valid_from",
            "valid_to",
            "created_at",
            "updated_at"
        ]

class AvailabilitySlotCreateUpdateSerializer(serializers.ModelSerializer):
    # Availability is mentor-level; an IG is optional. Allow omitting it or
    # passing null so a slot can apply across all of the mentor's IGs.
    ig = serializers.PrimaryKeyRelatedField(
        queryset=InterestGroup.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = MentorAvailabilitySlot
        fields = [
            "ig",
            "weekday",
            "start_time",
            "end_time",
            "timezone",
            "is_active",
            "valid_from",
            "valid_to"
        ]

    def validate(self, attrs):
        start_time = attrs.get('start_time', self.instance.start_time if self.instance else None)
        end_time = attrs.get('end_time', self.instance.end_time if self.instance else None)
        weekday = attrs.get('weekday', self.instance.weekday if self.instance else None)
        valid_from = attrs.get('valid_from', self.instance.valid_from if self.instance else None)
        valid_to = attrs.get('valid_to', self.instance.valid_to if self.instance else None)
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time.")
            
        if weekday is not None and (weekday < 1 or weekday > 7):
            raise serializers.ValidationError("Weekday must be between 1 (Mon) and 7 (Sun).")
            
        if valid_from and valid_to and valid_from > valid_to:
            raise serializers.ValidationError("Valid from date must be before or equal to valid to date.")
            
        return attrs

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        
        slot = MentorAvailabilitySlot.objects.create(
            mentor_user_id=user_id,
            created_by_id=user_id,
            updated_by_id=user_id,
            **validated_data
        )
        return slot

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.updated_by_id = user_id
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance

from db.mentor import MentorshipSessionUserLink

def _user_can_join_session(user_id, session):
    """
    Mirrors the visibility rules of AvailableSessionListAPI: IG sessions
    require active IG membership, campus sessions require a verified link
    to that college org, and company sessions are open to every
    authenticated user. Visibility filtering alone is not access control —
    this is the corresponding enforcement at join time.
    """
    if session.session_type == MentorshipSession.SessionType.IG_SESSION:
        from db.task import UserIgLink
        return UserIgLink.objects.filter(
            user_id=user_id, ig_id=session.entity_id, is_active=True,
        ).exists()
    if session.session_type == MentorshipSession.SessionType.CAMPUS_SESSION:
        from db.organization import UserOrganizationLink
        return UserOrganizationLink.objects.filter(
            user_id=user_id, org_id=session.entity_id, org__org_type='College', verified=True,
        ).exists()
    if session.session_type == MentorshipSession.SessionType.COMPANY_SESSION:
        return True
    return False


class ParticipantJoinSerializer(serializers.Serializer):
    def create(self, validated_data):
        user_id = self.context.get("user_id")
        session_id = self.context.get("session_id")

        with transaction.atomic():
            session = MentorshipSession.objects.select_for_update().filter(id=session_id).first()
            if not session:
                raise serializers.ValidationError("Session not found.")

            if session.status != MentorshipSession.Status.SCHEDULED:
                raise serializers.ValidationError("Only scheduled sessions can be joined.")

            if not _user_can_join_session(user_id, session):
                raise serializers.ValidationError("You are not eligible to join this session.")

            if session.max_participants:
                current_count = MentorshipSessionUserLink.objects.filter(session_id=session_id).count()
                if current_count >= session.max_participants:
                    raise serializers.ValidationError("Session has reached its maximum participant limit.")

            if MentorshipSessionUserLink.objects.filter(session_id=session_id, user_id=user_id).exists():
                raise serializers.ValidationError("You have already joined this session.")

            link = MentorshipSessionUserLink.objects.create(
                session_id=session_id,
                user_id=user_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
                attendance_status=MentorshipSessionUserLink.AttendanceStatus.INVITED
            )
        return link

class MentorAddParticipantSerializer(serializers.Serializer):
    muid = serializers.CharField(required=True)

    def create(self, validated_data):
        mentor_id = self.context.get("user_id")
        session_id = self.context.get("session_id")
        muid = validated_data.get("muid")
        
        from db.user import User
        user = User.objects.filter(muid=muid, suspended_at__isnull=True).first()
        if not user:
            raise serializers.ValidationError("User with this muid not found or is suspended.")

        with transaction.atomic():
            session = MentorshipSession.objects.select_for_update().filter(id=session_id).first()
            if not session:
                raise serializers.ValidationError("Session not found.")

            # Verify the logged-in mentor created this session
            if session.created_by_id != mentor_id:
                raise serializers.ValidationError("You do not have permission to add participants to this session.")

            if session.status != MentorshipSession.Status.SCHEDULED:
                raise serializers.ValidationError("Only scheduled sessions can accept participants.")

            if session.max_participants:
                current_count = MentorshipSessionUserLink.objects.filter(session_id=session_id).count()
                if current_count >= session.max_participants:
                    raise serializers.ValidationError("Session has reached its maximum participant limit.")

            if MentorshipSessionUserLink.objects.filter(session_id=session_id, user_id=user.id).exists():
                raise serializers.ValidationError("This user is already a participant of this session.")

            link = MentorshipSessionUserLink.objects.create(
                session_id=session_id,
                user_id=user.id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
                attendance_status=MentorshipSessionUserLink.AttendanceStatus.INVITED
            )
        return link


class ParticipantListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    mu_id = serializers.CharField(source='user.muid', read_only=True)

    # Session details — lets the participant-history view render a session
    # (title/time/meeting link) without an extra detail fetch per row.
    session_title = serializers.CharField(source="session.title", read_only=True)
    session_starts_at = serializers.DateTimeField(source="session.starts_at", read_only=True)
    session_ends_at = serializers.DateTimeField(source="session.ends_at", read_only=True)
    session_mode = serializers.CharField(source="session.mode", read_only=True)
    session_meeting_link = serializers.CharField(source="session.meeting_link", read_only=True)
    session_venue = serializers.CharField(source="session.venue", read_only=True)
    session_status = serializers.CharField(source="session.status", read_only=True)
    session_entity_id = serializers.CharField(source="session.entity_id", read_only=True)
    session_entity_name = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSessionUserLink
        fields = [
            "id",
            "session_id",
            "user_id",
            "user_full_name",
            "mu_id",
            "participant_role",
            "attendance_status",
            "progress_note",
            "feedback",
            "contributed_minutes",
            "created_at",
            "session_title",
            "session_starts_at",
            "session_ends_at",
            "session_mode",
            "session_meeting_link",
            "session_venue",
            "session_status",
            "session_entity_id",
            "session_entity_name",
        ]

    @staticmethod
    def build_ig_map(links):
        """
        Resolve the Interest Group name for a page of participant links in a
        single query. List views should call this and pass the result as
        ``context={"ig_map": ...}`` so ``get_session_entity_name`` does not fire
        one InterestGroup query per row (entity_id is a CharField, not a FK, so
        select_related cannot cover it).
        """
        ig_ids = {
            link.session.entity_id
            for link in links
            if getattr(link, "session", None) and link.session.entity_id
        }
        if not ig_ids:
            return {}
        return InterestGroup.objects.filter(id__in=ig_ids).in_bulk()

    def get_session_entity_name(self, obj):
        session = getattr(obj, "session", None)
        if not session or not session.entity_id:
            return None
        # All sessions are IG-scoped; resolve the Interest Group name. Prefer the
        # batch-resolved map injected by list views (avoids an N+1); fall back to
        # a single lookup for single-object responses that don't build a map.
        ig_map = self.context.get("ig_map")
        if ig_map is not None:
            ig = ig_map.get(session.entity_id)
            return ig.name if ig else None
        ig = InterestGroup.objects.filter(id=session.entity_id).first()
        return ig.name if ig else None

class ParticipantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSessionUserLink
        fields = [
            "attendance_status",
            "progress_note",
            "contributed_minutes"
        ]

    def validate(self, data):
        contributed_minutes = data.get('contributed_minutes')
        if contributed_minutes is not None and contributed_minutes <= 0:
            raise serializers.ValidationError("Contributed minutes must be greater than zero.")
        return data

class ParticipantFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSessionUserLink
        fields = ["feedback", "rating"]

    def validate(self, attrs):
        # Ensure at least one of feedback or rating is being submitted.
        if 'feedback' not in attrs and 'rating' not in attrs:
            raise serializers.ValidationError("At least one of 'feedback' or 'rating' must be provided.")

        # If feedback is provided, it cannot be an empty string.
        if 'feedback' in attrs and not attrs.get('feedback', '').strip():
            raise serializers.ValidationError({"feedback": "Feedback cannot be empty."})

        rating = attrs.get("rating")
        if 'rating' in attrs and rating is not None and not (1 <= rating <= 5):
            raise serializers.ValidationError({"rating": "Rating must be between 1 and 5."})

        if self.instance.attendance_status != MentorshipSessionUserLink.AttendanceStatus.ATTENDED:
            raise serializers.ValidationError("You can only leave feedback for sessions you have attended.")

        return attrs

class MentorActivitySerializer(serializers.Serializer):
    id = serializers.CharField()
    activity_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    date = serializers.DateTimeField()
    status = serializers.CharField(allow_null=True, required=False)


class AdminAssignMentorSerializer(serializers.Serializer):
    """
    Validates and performs bulk admin assignment of users as mentors.

    The caller supplies a list of user_muids plus tier-specific fields.
    All DB side-effects for every user in the list are executed inside a
    single atomic transaction — if validation passes for the whole batch.
    """

    from db.user import User as _User
    from db.organization import Organization as _Organization
    from utils.types import OrganizationType as _OrganizationType

    user_muids   = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        help_text="List of user muids to assign as mentor."
    )
    mentor_tier  = serializers.ChoiceField(choices=MentorApplication.MentorTier.choices)
    org_id       = serializers.CharField(required=False, allow_null=True, default=None)
    ig_ids       = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
        default=list,
        help_text="List of InterestGroup UUIDs — required for IG_MENTOR tier."
    )
    about        = serializers.CharField(required=False, allow_blank=True, default=None)
    expertise    = serializers.CharField(required=False, allow_blank=True, default=None)
    hours        = serializers.IntegerField(required=False, min_value=0, default=0)

    def validate(self, attrs):
        from db.user import User
        from db.organization import Organization
        from utils.types import OrganizationType

        tier   = attrs["mentor_tier"]
        errors = {}

        # ── Resolve all user_muids ──────────────────────────────────────────
        resolved_users = {}
        invalid_muids  = []
        for muid in attrs["user_muids"]:
            user = User.objects.filter(muid=muid, suspended_at__isnull=True).first()
            if user is None:
                invalid_muids.append(muid)
            else:
                resolved_users[muid] = user

        if invalid_muids:
            errors["user_muids"] = (
                f"The following muids are invalid or belong to suspended users: "
                f"{', '.join(invalid_muids)}"
            )

        # ── Tier-specific validation ────────────────────────────────────────
        if tier in (MentorApplication.MentorTier.CAMPUS_MENTOR, MentorApplication.MentorTier.COMPANY_MENTOR):
            org_id = attrs.get("org_id")
            if not org_id:
                errors["org_id"] = f"org_id is required for {tier}."
            else:
                expected_org_type = (
                    OrganizationType.COLLEGE.value
                    if tier == MentorApplication.MentorTier.CAMPUS_MENTOR
                    else OrganizationType.COMPANY.value
                )
                org = Organization.objects.filter(id=org_id, org_type=expected_org_type).first()
                if org is None:
                    errors["org_id"] = (
                        f"org_id must reference a valid {expected_org_type} organisation."
                    )
                else:
                    attrs["_org"] = org

        if tier == MentorApplication.MentorTier.IG_MENTOR:
            ig_ids = attrs.get("ig_ids") or []
            if not ig_ids:
                errors["ig_ids"] = "ig_ids (non-empty list) is required for IG_MENTOR."
            else:
                invalid_igs = [
                    ig_id for ig_id in ig_ids
                    if not InterestGroup.objects.filter(id=ig_id).exists()
                ]
                if invalid_igs:
                    errors["ig_ids"] = (
                        f"The following IG IDs are invalid: {', '.join(invalid_igs)}"
                    )

        if errors:
            raise serializers.ValidationError(errors)

        attrs["_resolved_users"] = resolved_users
        return attrs

    def create(self, validated_data):
        """
        Atomically create an APPROVED MentorApplication (source=ADMIN_ASSIGNED)
        per user and apply its approval side-effects (profile upsert, grant,
        role, IG links) via the shared _apply_application_approval helper.
        Idempotent: re-assigning an existing tier/org combination reactivates
        the grant rather than erroring. Returns the list of muids assigned.
        """
        admin_id      = self.context["user_id"]
        tier          = validated_data["mentor_tier"]
        org           = validated_data.get("_org")
        ig_ids        = validated_data.get("ig_ids") or []
        resolved_users = validated_data["_resolved_users"]
        now           = DateTimeUtils.get_current_utc_time()

        # Fetch the platform-wide Mentor role once (shared across all users)
        mentor_role = Role.objects.filter(title=RoleType.MENTOR.value).first()
        admin_user = User.objects.get(id=admin_id)

        with transaction.atomic():
            for muid, user in resolved_users.items():
                # 1. Create/update the single UserMentor profile
                profile_data = {
                    "about": validated_data.get("about"),
                    "expertise": validated_data.get("expertise"),
                    "hours": validated_data.get("hours", 0),
                }
                UserMentor.objects.get_or_create(
                    user=user,
                    defaults={
                        **profile_data,
                        "created_by_id": admin_id,
                        "updated_by_id": admin_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                )

                # 2. Create an approved MentorApplication record
                application, app_created = MentorApplication.objects.get_or_create(
                    user=user,
                    mentor_tier=tier,
                    org=org,
                    defaults={
                        "status": MentorApplication.Status.APPROVED,
                        "preferred_ig_ids": ig_ids if ig_ids else None,
                        "verified_by_id": admin_id,
                        "verified_at": now,
                        "created_by_id": admin_id,
                        "updated_by_id": admin_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                )
                if not app_created and application.status != MentorApplication.Status.APPROVED:
                    application.status = MentorApplication.Status.APPROVED
                    application.verified_by_id = admin_id
                    application.verified_at = now
                    application.save()

                # 3. Grant the tier being assigned (additive).
                if tier != MentorApplication.MentorTier.IG_MENTOR:
                    scope_id = str(org.id) if org else None
                    grant, grant_created = MentorScopeGrant.objects.get_or_create(
                        application=application,
                        scope_type=tier,
                        scope_id=scope_id,
                        defaults={
                            "is_active": True,
                            "granted_by_id": admin_id,
                            "granted_at": now,
                        },
                    )
                    if not grant_created and not grant.is_active:
                        grant.is_active = True
                        grant.revoked_by = None
                        grant.revoked_at = None
                        grant.save(update_fields=["is_active", "revoked_by", "revoked_at"])

                # 4. Assign global Mentor role
                if mentor_role:
                    UserRoleLink.objects.get_or_create(
                        user=user,
                        role=mentor_role,
                        defaults={"verified": True, "created_by_id": admin_id, "created_at": now}
                    )

                # Log the admin assignment action
                from db.mentor import SystemActionLog
                SystemActionLog.objects.create(
                    action_type=SystemActionLog.ActionType.MENTOR_VERIFY.value,
                    actor_user=admin_user,
                    subject_user=user,
                    entity_name='mentor_application',
                    entity_id=application.id,
                    new_data={
                        'status': application.status,
                        'mentor_tier': application.mentor_tier,
                        'org_id': str(application.org.id) if application.org else None,
                        'org_title': application.org.title if application.org else None,
                        'ig_ids': ig_ids,
                        'admin_assign': True
                    },
                    remarks=f"Admin {admin_user.full_name} directly assigned {user.full_name} as a {tier}."
                )

                # 5. Side-effects (IG links + org link)
                if ig_ids:
                    from .dash_mentor_helper import reconcile_mentor_ig_links, reconcile_mentor_ig_grants
                    reconcile_mentor_ig_links(user, ig_ids, admin_id)
                    reconcile_mentor_ig_grants(application, admin_id)

                if tier in (MentorApplication.MentorTier.CAMPUS_MENTOR, MentorApplication.MentorTier.COMPANY_MENTOR) and org:
                    from db.organization import UserOrganizationLink
                    UserOrganizationLink.objects.get_or_create(
                        user=user,
                        org=org,
                        defaults={"verified": True, "created_by_id": admin_id, "created_at": now}
                    )

        return list(resolved_users.keys())


class MentorDeactivationSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=500)


# ─────────────────────────────────────────────────────────────────────────────
# Student session-request serializers
# ─────────────────────────────────────────────────────────────────────────────

class StudentSessionRequestSerializer(serializers.ModelSerializer):
    """
    Used by students to create a session request.

    All sessions are Interest-Group scoped, so only ``ig_session`` requests are
    accepted; company/campus session types are rejected.

    Validates:
      - The session_type is ig_session and the student is a member of the target
        Interest Group (entity_id).
      - Time constraints (starts_at < ends_at, starts_at in future).
      - Mode / venue / meeting-link consistency (same rules as SessionCreateSerializer).
      - No duplicate pending request (same student + entity + title + starts_at).
    """

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "session_type",
            "entity_id",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "max_participants",
        ]

    def validate(self, attrs):
        from db.task import UserIgLink
        from django.utils import timezone

        user_id     = self.context["user_id"]
        session_type = attrs.get("session_type")
        entity_id    = attrs.get("entity_id")
        starts_at    = attrs.get("starts_at")
        ends_at      = attrs.get("ends_at")

        # ── Time guards ──────────────────────────────────────────────────────
        if starts_at and starts_at <= timezone.now():
            raise serializers.ValidationError(
                {"starts_at": "Session start time must be in the future."}
            )

        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError(
                "Session start time must be before end time."
            )

        # ── Entity-membership validation ─────────────────────────────────────
        # All sessions are Interest-Group scoped. Company- and campus-scoped
        # sessions are no longer supported, so any non-IG session_type is
        # rejected rather than persisted.
        if session_type != MentorshipSession.SessionType.IG_SESSION:
            raise serializers.ValidationError(
                {
                    "session_type": (
                        "Only Interest Group sessions can be requested. "
                        "Company- and campus-scoped sessions are not supported."
                    )
                }
            )

        if not UserIgLink.objects.filter(
            user_id=user_id,
            ig_id=entity_id,
            is_active=True,
        ).exists():
            raise serializers.ValidationError(
                {"entity_id": "You are not a member of this Interest Group."}
            )

        # ── Mode / venue / meeting-link constraints ──────────────────────────
        mode         = attrs.get("mode")
        venue        = (attrs.get("venue") or "").strip()
        meeting_link = (attrs.get("meeting_link") or "").strip()

        if mode == MentorshipSession.Mode.ONLINE and venue:
            raise serializers.ValidationError(
                {"venue": "Venue must not be provided for an online session."}
            )
        elif mode == MentorshipSession.Mode.OFFLINE and meeting_link:
            raise serializers.ValidationError(
                {"meeting_link": "Meeting link must not be provided for an offline session."}
            )
        elif mode == MentorshipSession.Mode.HYBRID:
            errors = {}
            if not venue:
                errors["venue"] = "Venue is required for a hybrid session."
            if not meeting_link:
                errors["meeting_link"] = "Meeting link is required for a hybrid session."
            if errors:
                raise serializers.ValidationError(errors)

        # ── Duplicate request guard ──────────────────────────────────────────
        if MentorshipSession.objects.filter(
            requested_by_id=user_id,
            entity_id=entity_id,
            title=attrs.get("title"),
            starts_at=starts_at,
            status=MentorshipSession.Status.REQUESTED,
            is_deleted=False,
        ).exists():
            raise serializers.ValidationError(
                "You already have a pending request for a session with the same "
                "title and start time for this entity."
            )

        return attrs

    def create(self, validated_data):
        user_id = self.context["user_id"]

        session = MentorshipSession.objects.create(
            status=MentorshipSession.Status.REQUESTED,
            requested_by_id=user_id,
            created_by_id=user_id,
            updated_by_id=user_id,
            **validated_data,
        )

        # Register the requesting student as an invited MENTEE immediately
        from db.mentor import MentorshipSessionUserLink
        MentorshipSessionUserLink.objects.create(
            session=session,
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
            attendance_status=MentorshipSessionUserLink.AttendanceStatus.INVITED,
        )

        return session


class StudentSessionRequestListSerializer(serializers.ModelSerializer):
    """
    Read-only serializer used by mentors to see incoming student session requests.
    Includes the requesting student's name for quick identification.
    """
    requested_by_name  = serializers.CharField(source="requested_by.full_name", read_only=True)
    requested_by_muid  = serializers.CharField(source="requested_by.muid",      read_only=True)
    entity_name        = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "session_type",
            "entity_id",
            "entity_name",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "max_participants",
            "status",
            "requested_by_id",
            "requested_by_name",
            "requested_by_muid",
            "created_at",
        ]

    def get_entity_name(self, obj):
        if obj.session_type == MentorshipSession.SessionType.IG_SESSION:
            ig = InterestGroup.objects.filter(id=obj.entity_id).first()
            return ig.name if ig else None
        elif obj.session_type in (
            MentorshipSession.SessionType.CAMPUS_SESSION,
            MentorshipSession.SessionType.COMPANY_SESSION,
        ):
            org = Organization.objects.filter(id=obj.entity_id).first()
            return org.title if org else None
        return None


class MentorStudentRequestVerifySerializer(serializers.Serializer):
    """
    Allows a mentor to approve or reject a student's session request.

    On APPROVE:
      - Optional overrides (starts_at, ends_at, mode, meeting_link, venue) are
        applied so the mentor can adjust the proposed time / logistics.
      - The session transitions from REQUESTED → SCHEDULED directly — mentor
        approval is the trust gate, there is no separate admin step.
      - created_by is updated to the approving mentor so the session appears in
        their dashboard and they can edit/cancel it using existing APIs.
      - requested_by is left untouched — permanent audit trail.

    On REJECT:
      - The session transitions from REQUESTED → REJECTED.
      - requested_by remains set; the student can view their rejected requests.
    """

    status       = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    # Optional mentor-provided overrides — applied only when status == APPROVED
    starts_at    = serializers.DateTimeField(required=False, allow_null=True)
    ends_at      = serializers.DateTimeField(required=False, allow_null=True)
    mode         = serializers.ChoiceField(
        choices=MentorshipSession.Mode.choices, required=False, allow_null=True
    )
    meeting_link = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    venue        = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        from django.utils import timezone

        action   = attrs.get("status")
        starts_at = attrs.get("starts_at")
        ends_at   = attrs.get("ends_at")

        if action == "APPROVED":
            # Resolve effective times (override or fall back to existing session values)
            effective_starts = starts_at or self.instance.starts_at
            effective_ends   = ends_at   or self.instance.ends_at

            if effective_starts <= timezone.now():
                raise serializers.ValidationError(
                    {"starts_at": "Session start time must be in the future."}
                )

            if effective_starts >= effective_ends:
                raise serializers.ValidationError(
                    "Session start time must be before end time."
                )

            # Resolve effective mode/venue/link for consistency check
            effective_mode  = attrs.get("mode")         or self.instance.mode
            effective_venue = (attrs.get("venue") or self.instance.venue or "").strip()
            effective_link  = (attrs.get("meeting_link") or self.instance.meeting_link or "").strip()

            if effective_mode == MentorshipSession.Mode.ONLINE and effective_venue:
                raise serializers.ValidationError(
                    {"venue": "Venue must not be provided for an online session."}
                )
            elif effective_mode == MentorshipSession.Mode.OFFLINE and effective_link:
                raise serializers.ValidationError(
                    {"meeting_link": "Meeting link must not be provided for an offline session."}
                )
            elif effective_mode == MentorshipSession.Mode.HYBRID:
                errors = {}
                if not effective_venue:
                    errors["venue"] = "Venue is required for a hybrid session."
                if not effective_link:
                    errors["meeting_link"] = "Meeting link is required for a hybrid session."
                if errors:
                    raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        mentor_id = self.context["user_id"]
        action    = validated_data["status"]

        if action == "APPROVED":
            # Apply optional mentor overrides
            override_fields = ["starts_at", "ends_at", "mode", "meeting_link", "venue"]
            for field in override_fields:
                value = validated_data.get(field)
                if value is not None:
                    setattr(instance, field, value)

            # Mentor approval is the trust gate — the session goes live directly
            # (no separate admin approval).
            instance.status         = MentorshipSession.Status.SCHEDULED
            instance.approved_by_id = mentor_id
            instance.approved_at    = DateTimeUtils.get_current_utc_time()
            instance.created_by_id  = mentor_id   # mentor takes ownership
            instance.updated_by_id  = mentor_id
            instance.save()

            MentorshipSessionUserLink.objects.get_or_create(
                session=instance,
                user_id=mentor_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
            )

        else:  # REJECTED
            instance.status        = MentorshipSession.Status.REJECTED
            instance.updated_by_id = mentor_id
            instance.save(update_fields=["status", "updated_by_id"])

        return instance
