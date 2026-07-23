import uuid
from rest_framework import serializers
import re
from db.user import Socials, UserMentor, UserRoleLink, Role, MentorScopeGrant


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
from db.task import InterestGroup, UserIgLink
from utils.types import RoleType
from utils.utils import DateTimeUtils
from django.db import transaction
from django.db.models import Q

class MentorRegisterSerializer(serializers.ModelSerializer):
    linkedin = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=200)

    class Meta:
        model = UserMentor
        fields = [
            "about",
            "expertise",
            "reason",
            "hours",
            "preferred_ig_ids",
            "linkedin"
        ]

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

    def create(self, validated_data):
        user_id = self.context["user_id"]
        linkedin_url = validated_data.pop('linkedin', None)

        if linkedin_url:
            reason = validated_data.get('reason', '')
            # Append linkedin url to reason for admin verification
            validated_data['reason'] = f"{reason}\n\n[LINKEDIN_URL_PENDING:{linkedin_url}]"
        
        mentor = UserMentor.objects.create(
            user_id=user_id,
            status=UserMentor.Status.PENDING,
            mentor_tier=UserMentor.MentorTier.IG_MENTOR,
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time(),
            updated_at=DateTimeUtils.get_current_utc_time(),
            **validated_data
        )
        return mentor

class MentorUpdateSerializer(serializers.ModelSerializer):
    linkedin = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=200)

    class Meta:
        model = UserMentor
        fields = [
            "about",
            "expertise",
            "reason",
            "hours",
            "preferred_ig_ids",
            "linkedin"
        ]

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

    def validate(self, data):
        # Every mentor must mentor at least one Interest Group (regardless of
        # tier or any org scope) — the IG list cannot be cleared to empty.
        instance = self.instance
        if instance and "preferred_ig_ids" in data and not data["preferred_ig_ids"]:
            raise serializers.ValidationError(
                {"preferred_ig_ids": "You must mentor at least one Interest Group."}
            )
        return data

    def update(self, instance, validated_data):
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_by_id'] = self.context.get("user_id", instance.user_id)

        igs_in_payload = "preferred_ig_ids" in validated_data
        validated_data.pop('linkedin', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Self-service: any APPROVED mentor (any tier) editing their Interest
        # Groups takes effect immediately — no admin re-approval. IG mentoring is
        # an orthogonal scope, so company/campus/global mentors can manage IGs too.
        # (The profile PATCH endpoint already restricts to APPROVED mentors.)
        if igs_in_payload and instance.status == UserMentor.Status.APPROVED:
            from .dash_mentor_helper import reconcile_mentor_ig_links, reconcile_mentor_ig_grants

            actor_id = self.context.get("user_id", instance.user_id)
            reconcile_mentor_ig_links(instance.user, instance.preferred_ig_ids, actor_id)
            reconcile_mentor_ig_grants(instance, instance.preferred_ig_ids, actor_id)

        return instance

class MentorListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)

    class Meta:
        model = UserMentor
        fields = [
            "id",
            "user_id",
            "user_full_name",
            "user_email",
            "muid",
            "about",
            "expertise",
            "verification_note",
            "verified_at",
            "mentor_tier",
            "status",
            "created_at",
            "updated_at"
        ]

class MentorDetailSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    company = serializers.SerializerMethodField()

    class Meta:
        model = UserMentor
        # Explicit list — this serializer is also used by
        # MentorPublicProfileAPI, so internal/audit-only columns
        # (verification_note, created_by, updated_by) must never appear
        # here regardless of what gets added to UserMentor in future.
        fields = [
            "id",
            "user",
            "user_full_name",
            "user_email",
            "about",
            "expertise",
            "reason",
            "hours",
            "mentor_tier",
            "status",
            "preferred_ig_ids",
            "org",
            "verified_by",
            "verified_at",
            "company",
            "created_at",
            "updated_at",
        ]

    def get_company(self, obj):
        from .dash_mentor_helper import get_mentor_company
        return get_mentor_company(obj)

class MentorVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[UserMentor.Status.APPROVED, UserMentor.Status.REJECTED])
    verification_note = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("status") == UserMentor.Status.REJECTED and not data.get("verification_note"):
            raise serializers.ValidationError("Verification note is required when rejecting.")
        return data

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        status = validated_data.get("status")

        # Handle special case for LinkedIn update request from profile
        if instance.about == "[LinkedIn URL Update Request]":
            if status == UserMentor.Status.APPROVED:
                linkedin_url = instance.expertise
                socials, _ = Socials.objects.get_or_create(
                    user=instance.user,
                    defaults={'created_by_id': user_id, 'updated_by_id': user_id}
                )
                socials.linkedin = linkedin_url
                socials.updated_by_id = user_id
                socials.save(update_fields=['linkedin', 'updated_by_id'])
                
                instance.delete()
                return instance
            else:  
                instance.status = UserMentor.Status.REJECTED
                instance.verification_note = validated_data.get("verification_note", "LinkedIn URL update rejected.")
                instance.updated_by_id = user_id
                instance.updated_at = DateTimeUtils.get_current_utc_time()
                instance.save()
                return instance
        
        instance.status = status
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        
        if status == UserMentor.Status.APPROVED:
            # Check for and process LinkedIn URL from reason field for new registrations
            if instance.reason and "[LINKEDIN_URL_PENDING:" in instance.reason:
                match = re.search(r'\[LINKEDIN_URL_PENDING:(.*?)\]', instance.reason, re.DOTALL)
                if match:
                    linkedin_url = match.group(1).strip()
                    if linkedin_url:
                        socials, _ = Socials.objects.get_or_create(
                            user=instance.user,
                            defaults={'created_by_id': user_id, 'updated_by_id': user_id}
                        )
                        socials.linkedin = linkedin_url
                        socials.updated_by_id = user_id
                        socials.save(update_fields=['linkedin', 'updated_by_id'])
                    
                    # Clean up the reason field
                    instance.reason = instance.reason.replace(match.group(0), '').strip()

            instance.verified_by_id = user_id
            instance.verified_at = DateTimeUtils.get_current_utc_time()

            # Grant the tier being approved. Additive — never touches any
            # other scope grant this mentor may already hold. IG_MENTOR is
            # excluded here: it has no single scope_id of its own — its
            # grants are always per-IG, created below via
            # reconcile_mentor_ig_grants from preferred_ig_ids. Creating a
            # scope_id=None IG_MENTOR grant here would be a meaningless
            # "mentor for no particular IG" row alongside the real ones.
            if instance.mentor_tier != UserMentor.MentorTier.IG_MENTOR:
                scope_id = str(instance.org_id) if instance.org_id else None
                grant, grant_created = MentorScopeGrant.objects.get_or_create(
                    mentor=instance,
                    scope_type=instance.mentor_tier,
                    scope_id=scope_id,
                    defaults={
                        "is_active": True,
                        "granted_by_id": user_id,
                        "granted_at": DateTimeUtils.get_current_utc_time(),
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
                        "created_at": DateTimeUtils.get_current_utc_time(),
                    },
                )
                if not created and not role_link.verified:
                    role_link.verified = True
                    role_link.save(update_fields=["verified"])

            # Auto-assign UserIgLink from preferred IGs for ANY tier — IG
            # mentoring is an orthogonal scope, so company/campus/global mentors
            # can also mentor Interest Groups. Uses the shared reconciler
            # (creates/reactivates chosen IGs, deactivates removed ones, only
            # touches MENTOR-type links).
            if instance.preferred_ig_ids:
                from .dash_mentor_helper import reconcile_mentor_ig_links, reconcile_mentor_ig_grants

                reconcile_mentor_ig_links(
                    instance.user, instance.preferred_ig_ids, user_id
                )
                reconcile_mentor_ig_grants(
                    instance, instance.preferred_ig_ids, user_id
                )

            # Auto-link COMPANY_MENTOR to the company's Organization
            if instance.mentor_tier == UserMentor.MentorTier.COMPANY_MENTOR and instance.org:
                from db.organization import UserOrganizationLink
                org_link, created = UserOrganizationLink.objects.get_or_create(
                    user=instance.user,
                    org=instance.org,
                    defaults={
                        "verified": True,
                        "created_by_id": user_id,
                        "created_at": DateTimeUtils.get_current_utc_time(),
                    },
                )
                if not created and not org_link.verified:
                    org_link.verified = True
                    org_link.save(update_fields=["verified"])

        elif status == UserMentor.Status.REJECTED:
            instance.verification_note = validated_data.get("verification_note")
            
        instance.save()
        return instance


from db.mentor import MentorshipSession
from db.organization import Organization
from db.task import InterestGroup
from .session_recurrence_helper import generate_recurring_sessions

class SessionCreateSerializer(serializers.ModelSerializer):
    child_session_ids = serializers.SerializerMethodField()

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
            "child_session_ids"
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

    def validate(self, data):
        user_id = self.context.get("user_id")
        if MentorshipSession.objects.filter(
            title=data.get('title'),
            starts_at=data.get('starts_at'),
            entity_id=data.get('entity_id'),
            created_by_id=user_id,
            is_deleted=False
        ).exists():
            raise serializers.ValidationError("A session with this exact title and start time already exists.")

        if data.get('starts_at') >= data.get('ends_at'):
            raise serializers.ValidationError("Session start time must be before end time.")

        # ── Mode / venue constraints ────────────────────────────────────────
        mode = data.get('mode')
        venue = data.get('venue') or ""
        meeting_link = data.get('meeting_link') or ""

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

        is_recurring = data.get('is_recurring', False)
        if is_recurring:
            errors = {}
            if not data.get('recurrence_type'):
                errors['recurrence_type'] = "recurrence_type is required when is_recurring is true."
            if not data.get('recurrence_interval') or data.get('recurrence_interval') < 1:
                errors['recurrence_interval'] = "recurrence_interval must be a positive integer when is_recurring is true."
            if not data.get('recurrence_end_date'):
                errors['recurrence_end_date'] = "recurrence_end_date is required when is_recurring is true."
            elif data.get('starts_at') and data.get('recurrence_end_date') <= data.get('starts_at').date():
                errors['recurrence_end_date'] = "recurrence_end_date must be after the session starts_at date."

            if errors:
                raise serializers.ValidationError(errors)
        else:
            data['recurrence_type'] = None
            data['recurrence_interval'] = None
            data['recurrence_end_date'] = None

        return data

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

            if session.is_recurring:
                child_sessions = generate_recurring_sessions(session)
                session._child_session_ids = [c.id for c in child_sessions]
            else:
                session._child_session_ids = []

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

    def validate(self, data):
        # Allow partial updates by fetching from instance if not in data
        starts_at = data.get('starts_at', self.instance.starts_at) if self.instance else data.get('starts_at')
        ends_at = data.get('ends_at', self.instance.ends_at) if self.instance else data.get('ends_at')

        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError("Session start time must be before end time.")

        # ── Mode / venue constraints (resolve from instance for partial PATCH) ──
        mode = data.get('mode', self.instance.mode if self.instance else None)
        venue = (data.get('venue') if 'venue' in data else (self.instance.venue if self.instance else None)) or ""
        meeting_link = (data.get('meeting_link') if 'meeting_link' in data else (self.instance.meeting_link if self.instance else None)) or ""

        # On a mode change we auto-clear the field that no longer applies rather
        # than rejecting stale data. Switching an online session to offline (or
        # vice-versa) would otherwise fail because the previous meeting_link /
        # venue is still stored on the row.
        if mode == MentorshipSession.Mode.ONLINE:
            data["venue"] = ""
        elif mode == MentorshipSession.Mode.OFFLINE:
            data["meeting_link"] = ""
        elif mode == MentorshipSession.Mode.HYBRID:
            errors = {}
            if not venue.strip():
                errors["venue"] = "Venue is required for a hybrid session."
            if not meeting_link.strip():
                errors["meeting_link"] = "Meeting link is required for a hybrid session."
            if errors:
                raise serializers.ValidationError(errors)

        return data

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

    def validate(self, data):
        start_time = data.get('start_time', self.instance.start_time if self.instance else None)
        end_time = data.get('end_time', self.instance.end_time if self.instance else None)
        weekday = data.get('weekday', self.instance.weekday if self.instance else None)
        valid_from = data.get('valid_from', self.instance.valid_from if self.instance else None)
        valid_to = data.get('valid_to', self.instance.valid_to if self.instance else None)
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time.")
            
        if weekday and (weekday < 1 or weekday > 7):
            raise serializers.ValidationError("Weekday must be between 1 (Mon) and 7 (Sun).")
            
        if valid_from and valid_to and valid_from > valid_to:
            raise serializers.ValidationError("Valid from date must be before or equal to valid to date.")
            
        return data

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

class ParticipantJoinSerializer(serializers.Serializer):
    def create(self, validated_data):
        user_id = self.context.get("user_id")
        session_id = self.context.get("session_id")
        
        session = MentorshipSession.objects.filter(id=session_id).first()
        if not session:
            raise serializers.ValidationError("Session not found.")
            
        if session.status != MentorshipSession.Status.SCHEDULED:
            raise serializers.ValidationError("Only scheduled sessions can be joined.")
            
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
            
        session = MentorshipSession.objects.filter(id=session_id).first()
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
        fields = ["feedback"]

    def validate(self, data):
        if not data.get("feedback"):
            raise serializers.ValidationError("Feedback cannot be empty.")
            
        if self.instance.attendance_status != MentorshipSessionUserLink.AttendanceStatus.ATTENDED:
            raise serializers.ValidationError("You can only leave feedback for sessions you have attended.")
            
        return data

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
    mentor_tier  = serializers.ChoiceField(choices=UserMentor.MentorTier.choices)
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

    def validate(self, data):
        from db.user import User
        from db.organization import Organization
        from utils.types import OrganizationType

        tier   = data["mentor_tier"]
        errors = {}

        # ── Resolve all user_muids ──────────────────────────────────────────
        resolved_users = {}
        invalid_muids  = []
        for muid in data["user_muids"]:
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
        if tier in (UserMentor.MentorTier.CAMPUS_MENTOR, UserMentor.MentorTier.COMPANY_MENTOR):
            org_id = data.get("org_id")
            if not org_id:
                errors["org_id"] = f"org_id is required for {tier}."
            else:
                expected_org_type = (
                    OrganizationType.COLLEGE.value
                    if tier == UserMentor.MentorTier.CAMPUS_MENTOR
                    else OrganizationType.COMPANY.value
                )
                org = Organization.objects.filter(id=org_id, org_type=expected_org_type).first()
                if org is None:
                    errors["org_id"] = (
                        f"org_id must reference a valid {expected_org_type} organisation."
                    )
                else:
                    data["_org"] = org

        if tier == UserMentor.MentorTier.IG_MENTOR:
            ig_ids = data.get("ig_ids") or []
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

        data["_resolved_users"] = resolved_users
        return data

    def create(self, validated_data):
        """
        Atomically create/update UserMentor records + all linked DB objects
        for every user in the bulk list.
        Returns the list of muids that were successfully assigned.
        """
        admin_id      = self.context["user_id"]
        tier          = validated_data["mentor_tier"]
        org           = validated_data.get("_org")
        ig_ids        = validated_data.get("ig_ids") or []
        resolved_users = validated_data["_resolved_users"]
        now           = DateTimeUtils.get_current_utc_time()

        # Fetch the platform-wide Mentor role once (shared across all users)
        mentor_role = Role.objects.filter(title=RoleType.MENTOR.value).first()

        with transaction.atomic():
            for muid, user in resolved_users.items():
                # ── 1. Create / update UserMentor record ───────────────────
                mentor_record, _ = UserMentor.objects.get_or_create(
                    user=user,
                    mentor_tier=tier,
                    org=org,
                    defaults={
                        "status":      UserMentor.Status.APPROVED,
                        "about":       validated_data.get("about"),
                        "expertise":   validated_data.get("expertise"),
                        "hours":       validated_data.get("hours", 0),
                        "preferred_ig_ids": ig_ids if ig_ids else None,
                        "verified_by_id":   admin_id,
                        "verified_at":      now,
                        "updated_by_id":    admin_id,
                        "updated_at":       now,
                        "created_by_id":    admin_id,
                        "created_at":       now,
                    },
                )
                # Idempotent: if it already exists, force-approve it
                if mentor_record.status != UserMentor.Status.APPROVED:
                    mentor_record.status       = UserMentor.Status.APPROVED
                    mentor_record.verified_by_id = admin_id
                    mentor_record.verified_at  = now
                    mentor_record.updated_by_id = admin_id
                    mentor_record.updated_at   = now
                    mentor_record.save(update_fields=[
                        "status", "verified_by_id", "verified_at",
                        "updated_by_id", "updated_at",
                    ])

                # ── 1b. Grant the tier being assigned (additive). IG_MENTOR
                # is excluded — it has no single scope_id of its own; its
                # grants are per-IG, created in the ig_ids loop below.
                if tier != UserMentor.MentorTier.IG_MENTOR:
                    scope_id = str(org.id) if org else None
                    grant, grant_created = MentorScopeGrant.objects.get_or_create(
                        mentor=mentor_record,
                        scope_type=tier,
                        scope_id=scope_id,
                        defaults={
                            "is_active":     True,
                            "granted_by_id": admin_id,
                            "granted_at":    now,
                        },
                    )
                    if not grant_created and not grant.is_active:
                        grant.is_active = True
                        grant.revoked_by = None
                        grant.revoked_at = None
                        grant.save(update_fields=["is_active", "revoked_by", "revoked_at"])

                # ── 2. Assign global Mentor role ────────────────────────────
                if mentor_role:
                    role_link, created = UserRoleLink.objects.get_or_create(
                        user=user,
                        role=mentor_role,
                        defaults={
                            "verified":    True,
                            "created_by_id": admin_id,
                            "created_at":  now,
                        },
                    )
                    if not created and not role_link.verified:
                        role_link.verified = True
                        role_link.save(update_fields=["verified"])

                # ── 3. Side-effects (IG links + org link can coexist) ───────
                # Every mentor tier can mentor Interest Groups, so create MENTOR
                # UserIgLink rows for ANY tier whenever ig_ids are supplied —
                # not just IG_MENTOR. Without this, a company/campus mentor's
                # preferred_ig_ids snapshot would be saved while the authoritative
                # UserIgLink rows (used by session-create + the IG dropdown) stay
                # empty, leaving them unable to create sessions for IGs they
                # appear to mentor.
                if ig_ids:
                    for ig_id in ig_ids:
                        ig = InterestGroup.objects.filter(id=ig_id).first()
                        if ig:
                            ig_link, created = UserIgLink.objects.get_or_create(
                                user=user,
                                ig=ig,
                                defaults={
                                    "assignment_type": UserIgLink.AssignmentType.MENTOR,
                                    "is_active":       True,
                                    "assigned_by_id":  admin_id,
                                    "created_by_id":   admin_id,
                                    "created_at":      now,
                                },
                            )
                            if not created:
                                ig_link.assignment_type = UserIgLink.AssignmentType.MENTOR
                                ig_link.is_active       = True
                                ig_link.assigned_by_id  = admin_id
                                ig_link.save(update_fields=["assignment_type", "is_active", "assigned_by_id"])

                            ig_grant, ig_grant_created = MentorScopeGrant.objects.get_or_create(
                                mentor=mentor_record,
                                scope_type=MentorScopeGrant.ScopeType.IG_MENTOR,
                                scope_id=str(ig_id),
                                defaults={
                                    "is_active":     True,
                                    "granted_by_id": admin_id,
                                    "granted_at":    now,
                                },
                            )
                            if not ig_grant_created and not ig_grant.is_active:
                                ig_grant.is_active = True
                                ig_grant.revoked_by = None
                                ig_grant.revoked_at = None
                                ig_grant.save(update_fields=["is_active", "revoked_by", "revoked_at"])

                # Company/campus mentors also get their verified org link.
                if tier in (UserMentor.MentorTier.CAMPUS_MENTOR, UserMentor.MentorTier.COMPANY_MENTOR) and org:
                    from db.organization import UserOrganizationLink
                    org_link, created = UserOrganizationLink.objects.get_or_create(
                        user=user,
                        org=org,
                        defaults={
                            "verified":    True,
                            "created_by_id": admin_id,
                            "created_at":  now,
                        },
                    )
                    if not created and not org_link.verified:
                        org_link.verified = True
                        org_link.save(update_fields=["verified"])

        return list(resolved_users.keys())


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

    def validate(self, data):
        from db.task import UserIgLink
        from django.utils import timezone

        user_id     = self.context["user_id"]
        session_type = data.get("session_type")
        entity_id    = data.get("entity_id")
        starts_at    = data.get("starts_at")
        ends_at      = data.get("ends_at")

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
        mode         = data.get("mode")
        venue        = (data.get("venue") or "").strip()
        meeting_link = (data.get("meeting_link") or "").strip()

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
            title=data.get("title"),
            starts_at=starts_at,
            status=MentorshipSession.Status.REQUESTED,
            is_deleted=False,
        ).exists():
            raise serializers.ValidationError(
                "You already have a pending request for a session with the same "
                "title and start time for this entity."
            )

        return data

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
      - The session transitions from REQUESTED → PENDING_APPROVAL.
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

    def validate(self, data):
        from django.utils import timezone

        action   = data.get("status")
        starts_at = data.get("starts_at")
        ends_at   = data.get("ends_at")

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
            effective_mode  = data.get("mode")         or self.instance.mode
            effective_venue = (data.get("venue") or self.instance.venue or "").strip()
            effective_link  = (data.get("meeting_link") or self.instance.meeting_link or "").strip()

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

        return data

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

        else:  # REJECTED
            instance.status        = MentorshipSession.Status.REJECTED
            instance.updated_by_id = mentor_id
            instance.save(update_fields=["status", "updated_by_id"])

        return instance
