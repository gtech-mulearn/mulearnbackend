from rest_framework import serializers

from db.mentor import (
    IgOpportunity,
    MentorAvailabilitySlot,
    MentorKarmaAward,
    MentorshipSession,
    MentorshipSessionUserLink,
    SystemActionLog,
)
from db.task import KarmaActivityLog
from db.mentor_task_request import MentorTaskRequest
from db.task import InterestGroup, KarmaActivityLog, TaskList, TaskType
from db.user import User, UserMentor


# ─────────────────────────────────────────────────────────────────────────────
# Onboarding
# ─────────────────────────────────────────────────────────────────────────────

class MentorOnboardingSerializer(serializers.ModelSerializer):
    """Create a new UserMentor row (first-time application)."""

    class Meta:
        model = UserMentor
        fields = ["about", "expertise", "reason", "preferred_ig_ids", "created_by", "updated_by"]
        extra_kwargs = {
            "preferred_ig_ids": {"required": False},
            "created_by": {"required": True},
            "updated_by": {"required": True},
        }

    def validate_preferred_ig_ids(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError("preferred_ig_ids must be a list of UUIDs.")
        return value


class MentorOnboardingUpdateSerializer(serializers.ModelSerializer):
    """Partial update of mentor's own profile fields."""

    class Meta:
        model = UserMentor
        fields = ["about", "expertise", "reason", "preferred_ig_ids", "updated_by"]
        extra_kwargs = {
            "updated_by": {"required": True},
            "preferred_ig_ids": {"required": False},
        }

    def validate_preferred_ig_ids(self, value):
        if value is not None and not isinstance(value, list):
            raise serializers.ValidationError("preferred_ig_ids must be a list of UUIDs.")
        return value


# ─────────────────────────────────────────────────────────────────────────────
# Mentor roster
# ─────────────────────────────────────────────────────────────────────────────

class MentorListSerializer(serializers.ModelSerializer):
    """Full mentor profile for admin roster view."""

    full_name = serializers.CharField(source="user.full_name")
    email = serializers.EmailField(source="user.email")
    muid = serializers.CharField(source="user.muid")
    profile_pic = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = UserMentor
        fields = [
            "id",
            "full_name",
            "email",
            "muid",
            "profile_pic",
            "about",
            "expertise",
            "reason",
            "hours",
            "mentor_tier",
            "is_verified",
            "verified_by_name",
            "verified_at",
            "verification_note",
            "created_at",
        ]

    def get_profile_pic(self, obj):
        return obj.user.profile_pic

    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return obj.verified_by.full_name
        return None


class MentorVerifySerializer(serializers.ModelSerializer):
    """Admin verifies / rejects a mentor application."""

    class Meta:
        model = UserMentor
        fields = [
            "is_verified",
            "mentor_tier",
            "verification_note",
            "verified_by",
            "verified_at",
            "updated_by",
        ]
        extra_kwargs = {
            "verified_by": {"required": True},
            "updated_by": {"required": True},
        }


# ─────────────────────────────────────────────────────────────────────────────
# Sessions
# ─────────────────────────────────────────────────────────────────────────────

class MentorSessionParticipantSerializer(serializers.ModelSerializer):
    """Read participant details for a session."""

    full_name = serializers.CharField(source="user.full_name")
    email = serializers.EmailField(source="user.email")
    muid = serializers.CharField(source="user.muid")

    class Meta:
        model = MentorshipSessionUserLink
        fields = [
            "id",
            "user_id",
            "full_name",
            "email",
            "muid",
            "participant_role",
            "attendance_status",
            "progress_note",
            "contributed_minutes",
            "created_at",
        ]


class MentorSessionListSerializer(serializers.ModelSerializer):
    """Session list with ig name and participant count."""

    ig_name = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.full_name")
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "status",
            "is_global",
            "ig_id",
            "ig_name",
            "created_by_name",
            "created_at",
            "participant_count",
            "max_participants",
        ]

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None

    def get_participant_count(self, obj):
        return obj.participants.count()


class MentorSessionDetailSerializer(serializers.ModelSerializer):
    """Session detail with all participants embedded."""

    ig_name = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.full_name")
    updated_by_name = serializers.CharField(source="updated_by.full_name")
    approved_by_name = serializers.SerializerMethodField()
    participants = MentorSessionParticipantSerializer(many=True, read_only=True)

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "status",
            "is_global",
            "ig_id",
            "ig_name",
            "approved_by_name",
            "approved_at",
            "created_by_name",
            "created_at",
            "updated_by_name",
            "updated_at",
            "max_participants",
            "participants",
        ]

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None

    def get_approved_by_name(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None


class MentorSessionCreateSerializer(serializers.ModelSerializer):
    """Create a mentorship session (admin IG session or mentor global session)."""

    class Meta:
        model = MentorshipSession
        fields = [
            "ig",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "is_global",
            "status",
            "max_participants",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "ig": {"required": False, "allow_null": True},
            "is_global": {"required": False},
            "status": {"required": False},
            "venue": {"required": False, "allow_null": True},
            "max_participants": {"required": False, "allow_null": True},
            "created_by": {"required": True},
            "updated_by": {"required": True},
        }

    def validate(self, attrs):
        from utils.utils import DateTimeUtils
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        now = DateTimeUtils.get_current_utc_time()
        
        if starts_at and ends_at:
            if starts_at >= ends_at:
                raise serializers.ValidationError("starts_at must be before ends_at.")
        if starts_at and starts_at < now:
            raise serializers.ValidationError("starts_at cannot be in the past.")

        mode = attrs.get("mode", MentorshipSession.Mode.ONLINE)
        venue = attrs.get("venue")
        meeting_link = attrs.get("meeting_link")

        if mode == MentorshipSession.Mode.ONLINE:
            if not meeting_link:
                raise serializers.ValidationError({"meeting_link": "Meeting link is required for ONLINE sessions."})
        elif mode == MentorshipSession.Mode.OFFLINE:
            if not venue:
                raise serializers.ValidationError({"venue": "Venue is required for OFFLINE sessions."})
        elif mode == MentorshipSession.Mode.HYBRID:
            if not meeting_link and not venue:
                raise serializers.ValidationError("At least one of meeting_link or venue is required for HYBRID sessions.")

        return attrs


class MentorSessionUpdateSerializer(serializers.ModelSerializer):
    """Update editable fields on a session (cannot change ig or is_global)."""

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
            "max_participants",
            "updated_by",
        ]
        extra_kwargs = {
            "updated_by": {"required": True},
            "venue": {"required": False, "allow_null": True},
            "max_participants": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):

        starts_at = attrs.get("starts_at", self.instance.starts_at if self.instance else None)
        ends_at = attrs.get("ends_at", self.instance.ends_at if self.instance else None)
        
        if starts_at and ends_at:
            if starts_at >= ends_at:
                raise serializers.ValidationError("starts_at must be before ends_at.")

        mode = attrs.get("mode", getattr(self.instance, "mode", MentorshipSession.Mode.ONLINE))
        venue = attrs.get("venue", getattr(self.instance, "venue", None))
        meeting_link = attrs.get("meeting_link", getattr(self.instance, "meeting_link", None))

        if mode == MentorshipSession.Mode.ONLINE:
            if not meeting_link:
                raise serializers.ValidationError({"meeting_link": "Meeting link is required for ONLINE sessions."})
        elif mode == MentorshipSession.Mode.OFFLINE:
            if not venue:
                raise serializers.ValidationError({"venue": "Venue is required for OFFLINE sessions."})
        elif mode == MentorshipSession.Mode.HYBRID:
            if not meeting_link and not venue:
                raise serializers.ValidationError("At least one of meeting_link or venue is required for HYBRID sessions.")

        return attrs


class MentorSessionStatusSerializer(serializers.ModelSerializer):
    """Update only the status of a session."""

    class Meta:
        model = MentorshipSession
        fields = ["status", "updated_by"]
        extra_kwargs = {"updated_by": {"required": True}}


class MentorSessionParticipantAddSerializer(serializers.ModelSerializer):
    """Add a participant to a session."""

    class Meta:
        model = MentorshipSessionUserLink
        fields = ["session", "user", "participant_role"]
        extra_kwargs = {
            "session": {"required": True},
            "user": {"required": True},
            "participant_role": {"required": True},
        }


# ─────────────────────────────────────────────────────────────────────────────
# Availability
# ─────────────────────────────────────────────────────────────────────────────

class MentorAvailabilitySerializer(serializers.ModelSerializer):
    """Read availability slots."""

    ig_name = serializers.SerializerMethodField()
    mentor_full_name = serializers.CharField(source="mentor_user.full_name")

    class Meta:
        model = MentorAvailabilitySlot
        fields = [
            "id",
            "mentor_user_id",
            "mentor_full_name",
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
        ]

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None


class MentorAvailabilityWriteSerializer(serializers.ModelSerializer):
    """Create or fully replace an availability slot."""

    class Meta:
        model = MentorAvailabilitySlot
        fields = [
            "mentor_user",
            "ig",
            "weekday",
            "start_time",
            "end_time",
            "timezone",
            "valid_from",
            "valid_to",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "ig": {"required": False, "allow_null": True},
            "timezone": {"required": False},
            "valid_from": {"required": False, "allow_null": True},
            "valid_to": {"required": False, "allow_null": True},
            "created_by": {"required": True},
            "updated_by": {"required": True},
        }

    def validate(self, attrs):
        start_time = attrs.get("start_time", self.instance.start_time if self.instance else None)
        end_time = attrs.get("end_time", self.instance.end_time if self.instance else None)
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("start_time must be before end_time.")
        return attrs


# ─────────────────────────────────────────────────────────────────────────────
# Task Requests
# ─────────────────────────────────────────────────────────────────────────────

class MentorTaskRequestSerializer(serializers.ModelSerializer):
    """Read task request details."""

    mentor_name = serializers.CharField(source="mentor.full_name")
    ig_name = serializers.CharField(source="ig.name")
    reviewed_by_name = serializers.SerializerMethodField()
    created_task_title = serializers.SerializerMethodField()

    class Meta:
        model = MentorTaskRequest
        fields = [
            "id",
            "mentor_name",
            "ig_name",
            "ig_id",
            "title",
            "hashtag",
            "karma",
            "description",
            "status",
            "admin_note",
            "reviewed_by_name",
            "reviewed_at",
            "created_task_id",
            "created_task_title",
            "created_at",
        ]

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by else None

    def get_created_task_title(self, obj):
        return obj.created_task.title if obj.created_task else None


class MentorTaskRequestCreateSerializer(serializers.ModelSerializer):
    """Mentor submits a new task proposal."""

    class Meta:
        model = MentorTaskRequest
        fields = [
            "mentor",
            "ig",
            "title",
            "hashtag",
            "karma",
            "description",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "description": {"required": False, "allow_null": True},
            "created_by": {"required": True},
            "updated_by": {"required": True},
        }

    def validate_hashtag(self, value):
        if not value:
            raise serializers.ValidationError("Hashtag cannot be empty.")
            
        value = value.strip().lower()
        if not value.startswith("#"):
            value = f"#{value}"

        if TaskList.objects.filter(hashtag=value).exists():
            raise serializers.ValidationError("A task/request with this hashtag already exists.")
            
        if MentorTaskRequest.objects.filter(hashtag=value, status__in=[MentorTaskRequest.Status.PENDING, MentorTaskRequest.Status.APPROVED]).select_for_update().exists():
            raise serializers.ValidationError("A task/request with this hashtag already exists.")
            
        return value


class MentorTaskRequestReviewSerializer(serializers.ModelSerializer):
    """Admin approves or rejects a mentor task request."""

    status = serializers.ChoiceField(
        choices=[
            MentorTaskRequest.Status.APPROVED.value,
            MentorTaskRequest.Status.REJECTED.value,
        ]
    )

    class Meta:
        model = MentorTaskRequest
        fields = ["status", "admin_note", "reviewed_by", "reviewed_at", "updated_by"]
        extra_kwargs = {
            "reviewed_by": {"required": True},
            "reviewed_at": {"required": True},
            "updated_by": {"required": True},
        }


# ─────────────────────────────────────────────────────────────────────────────
# Opportunities
# ─────────────────────────────────────────────────────────────────────────────

class IgOpportunitySerializer(serializers.ModelSerializer):
    """Read opportunities with IG name."""

    ig_name = serializers.CharField(source="ig.name")
    created_by_name = serializers.CharField(source="created_by.full_name")

    class Meta:
        model = IgOpportunity
        fields = [
            "id",
            "ig_id",
            "ig_name",
            "type",
            "title",
            "description",
            "eligibility",
            "application_url",
            "starts_at",
            "ends_at",
            "status",
            "created_by_name",
            "created_at",
            "updated_at",
        ]


class IgOpportunityWriteSerializer(serializers.ModelSerializer):
    """Create / update an opportunity."""

    class Meta:
        model = IgOpportunity
        fields = [
            "ig",
            "type",
            "title",
            "description",
            "eligibility",
            "application_url",
            "starts_at",
            "ends_at",
            "status",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "eligibility": {"required": False, "allow_null": True},
            "application_url": {"required": False, "allow_null": True},
            "starts_at": {"required": False, "allow_null": True},
            "ends_at": {"required": False, "allow_null": True},
            "status": {"required": False},
            "created_by": {"required": True},
            "updated_by": {"required": True},
        }

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        
        if starts_at and ends_at:
            if starts_at >= ends_at:
                raise serializers.ValidationError("starts_at must be before ends_at.")
        return attrs


# ─────────────────────────────────────────────────────────────────────────────
# Activity Log
# ─────────────────────────────────────────────────────────────────────────────

class SystemActionLogSerializer(serializers.ModelSerializer):
    """Read-only audit log entries."""

    actor_name = serializers.CharField(source="actor_user.full_name")
    subject_name = serializers.SerializerMethodField()
    ig_name = serializers.SerializerMethodField()

    class Meta:
        model = SystemActionLog
        fields = [
            "id",
            "action_type",
            "actor_name",
            "subject_name",
            "ig_name",
            "entity_name",
            "entity_id",
            "old_data",
            "new_data",
            "remarks",
            "created_at",
        ]

    def get_subject_name(self, obj):
        return obj.subject_user.full_name if obj.subject_user else None

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None


# ─────────────────────────────────────────────────────────────────────────────
# Karma Award (Feature 1)
# ─────────────────────────────────────────────────────────────────────────────

class MentorKarmaAwardSerializer(serializers.ModelSerializer):
    """Read an existing karma award record."""

    mentor_name   = serializers.CharField(source="mentor.full_name")
    awarded_by_name = serializers.CharField(source="awarded_by.full_name")
    session_title = serializers.CharField(source="session.title")

    class Meta:
        model = MentorKarmaAward
        fields = [
            "id",
            "session_id",
            "session_title",
            "mentor_id",
            "mentor_name",
            "karma",
            "note",
            "awarded_by_name",
            "awarded_at",
            "kal_id",
            "created_at",
        ]


class MentorKarmaAwardWriteSerializer(serializers.Serializer):
    """Admin awards karma to a mentor for a completed session."""

    mentor_id = serializers.CharField(max_length=36)
    karma     = serializers.IntegerField(min_value=1)
    note      = serializers.CharField(max_length=500, required=False, allow_blank=True)


# ─────────────────────────────────────────────────────────────────────────────
# Task Review Queue (Feature 2)
# ─────────────────────────────────────────────────────────────────────────────

class KarmaReviewQueueSerializer(serializers.ModelSerializer):
    """KarmaActivityLog entry shown in the mentor review queue."""

    user_name     = serializers.CharField(source="user.full_name")
    user_muid     = serializers.CharField(source="user.muid")
    task_title    = serializers.CharField(source="task.title")
    task_hashtag  = serializers.CharField(source="task.hashtag")
    ig_name       = serializers.SerializerMethodField()

    class Meta:
        model = KarmaActivityLog
        fields = [
            "id",
            "user_name",
            "user_muid",
            "task_title",
            "task_hashtag",
            "ig_name",
            "karma",
            "mentor_review_status",
            "mentor_reviewed_at",
            "mentor_review_feedback",
            "created_at",
        ]

    def get_ig_name(self, obj):
        return obj.task.ig.name if (obj.task and obj.task.ig) else None


class KarmaReviewSerializer(serializers.Serializer):
    """Mentor sets review status on a KarmaActivityLog entry."""

    status   = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    feedback = serializers.CharField(max_length=500, required=False, allow_blank=True)


# ─────────────────────────────────────────────────────────────────────────────
# Leaderboard (Feature 3)
# ─────────────────────────────────────────────────────────────────────────────

class MentorLeaderboardSerializer(serializers.Serializer):
    """One row in the mentor leaderboard."""

    rank              = serializers.IntegerField()
    mentor_id         = serializers.CharField()
    full_name         = serializers.CharField()
    muid              = serializers.CharField()
    profile_pic       = serializers.CharField(allow_null=True)
    mentor_tier       = serializers.CharField()
    sessions_completed = serializers.IntegerField()
    mentees_attended  = serializers.IntegerField()
    hours             = serializers.IntegerField()
    score             = serializers.IntegerField()


# ─────────────────────────────────────────────────────────────────────────────
# Global Session with IG Suggestions (Feature 6)
# ─────────────────────────────────────────────────────────────────────────────

class GlobalSessionPendingSerializer(MentorSessionListSerializer):
    """Extends the list serializer with IG keyword-match suggestions."""

    suggested_igs = serializers.SerializerMethodField()

    class Meta(MentorSessionListSerializer.Meta):
        fields = MentorSessionListSerializer.Meta.fields + ["suggested_igs"]

    def get_suggested_igs(self, obj):
        """Top-3 IGs by keyword overlap with session title+description."""
        suggestions = self.context.get("ig_suggestions", {})
        return suggestions.get(obj.id, [])


# ─────────────────────────────────────────────────────────────────────────────
# Mentee Detail (endpoint 1)
# ─────────────────────────────────────────────────────────────────────────────

class MenteeDetailSerializer(serializers.Serializer):
    """Full profile of a single mentee as seen by a mentor or admin."""

    user_id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField()
    muid = serializers.CharField()
    total_sessions = serializers.IntegerField()
    completed_sessions = serializers.IntegerField()
    total_karma_earned = serializers.IntegerField()
    tasks_reviewed = serializers.IntegerField()
    tasks_approved = serializers.IntegerField()
    tasks_rejected = serializers.IntegerField()
    sessions = serializers.ListField(child=serializers.DictField())


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Attendance Update (endpoint 2)
# ─────────────────────────────────────────────────────────────────────────────

class AttendanceEntrySerializer(serializers.Serializer):
    """Single participant attendance update entry."""

    user_id = serializers.CharField(max_length=36)
    attendance_status = serializers.ChoiceField(
        choices=[s.value for s in MentorshipSessionUserLink.AttendanceStatus]
    )


class MentorSessionAttendanceSerializer(serializers.Serializer):
    """Bulk attendance update — list of (user_id, attendance_status) pairs."""

    participants = AttendanceEntrySerializer(many=True, min_length=1)


# ─────────────────────────────────────────────────────────────────────────────
# Admin Tier Update (endpoint 10)
# ─────────────────────────────────────────────────────────────────────────────

class MentorTierUpdateSerializer(serializers.Serializer):
    """Admin changes a verified mentor's tier."""

    mentor_tier = serializers.ChoiceField(
        choices=[t.value for t in UserMentor.MentorTier]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Public Session List (endpoint 5)
# ─────────────────────────────────────────────────────────────────────────────

class PublicMentorSessionSerializer(serializers.ModelSerializer):
    """Completed session entry for a mentor's public profile."""

    ig_name = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "title",
            "mode",
            "ig_name",
            "starts_at",
            "ends_at",
            "participant_count",
        ]

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None

    def get_participant_count(self, obj):
        return obj.participants.count()


# ─────────────────────────────────────────────────────────────────────────────
# Public endpoints
# ─────────────────────────────────────────────────────────────────────────────

class PublicMentorCardSerializer(serializers.ModelSerializer):
    """Public read-only profile for frontend mentor discovery pages."""
    full_name = serializers.CharField(source="user.full_name")
    muid = serializers.CharField(source="user.muid")
    profile_pic = serializers.CharField(source="user.profile_pic", allow_null=True)
    linked_igs = serializers.SerializerMethodField()
    availability_slots = serializers.SerializerMethodField()
    session_stats = serializers.SerializerMethodField()

    class Meta:
        model = UserMentor
        fields = [
            "full_name",
            "muid",
            "profile_pic",
            "about",
            "expertise",
            "mentor_tier",
            "linked_igs",
            "availability_slots",
            "session_stats",
        ]

    def get_linked_igs(self, obj):
        from db.task import UserIgLink
        links = UserIgLink.objects.filter(
            user_id=obj.user_id,
            assignment_type=UserIgLink.AssignmentType.MENTOR,
            is_active=True
        ).select_related("ig")
        return [{"ig_id": link.ig_id, "name": link.ig.name} for link in links if link.ig]

    def get_availability_slots(self, obj):
        from db.mentor import MentorAvailabilitySlot
        slots = MentorAvailabilitySlot.objects.filter(mentor_user_id=obj.user_id, is_active=True)
        return MentorAvailabilitySerializer(slots, many=True).data

    def get_session_stats(self, obj):
        from db.mentor import MentorshipSessionUserLink, MentorshipSession
        links = MentorshipSessionUserLink.objects.filter(
            user_id=obj.user_id,
            participant_role__in=[
                MentorshipSessionUserLink.ParticipantRole.MENTOR, 
                MentorshipSessionUserLink.ParticipantRole.CO_MENTOR
            ]
        ).values_list("session_id", flat=True)
        completed = MentorshipSession.objects.filter(id__in=links, status=MentorshipSession.Status.COMPLETED).count()
        return {"completed_sessions": completed, "hours": obj.hours}


# ─────────────────────────────────────────────────────────────────────────────
# Org-Mentor Serializers (Company and Campus)
# ─────────────────────────────────────────────────────────────────────────────

class OrgMentorOnboardingSerializer(serializers.ModelSerializer):
    """Base create serializer for Company/Campus mentor onboarding.
    Subclasses set mentor_tier; context['expected_org_type'] validates org."""

    class Meta:
        model = UserMentor
        fields = [
            "about", "expertise", "reason",
            "mentor_tier", "org",
            "created_by", "updated_by",
        ]
        extra_kwargs = {
            "about":       {"required": False, "allow_null": True},
            "expertise":   {"required": False, "allow_null": True},
            "reason":      {"required": False, "allow_null": True},
            "mentor_tier": {"required": True},
            "org":         {"required": True},
            "created_by":  {"required": True},
            "updated_by":  {"required": True},
        }

    def validate_org(self, org):
        expected_type = self.context.get("expected_org_type")
        if expected_type and org.org_type != expected_type:
            raise serializers.ValidationError(
                f"Organization must be type '{expected_type}', got '{org.org_type}'."
            )
        return org


class CompanyMentorOnboardingSerializer(OrgMentorOnboardingSerializer):
    """Create a COMPANY_MENTOR row (org.org_type must be 'Company')."""

    def validate(self, attrs):
        attrs["mentor_tier"] = UserMentor.MentorTier.COMPANY_MENTOR
        return attrs


class CampusMentorOnboardingSerializer(OrgMentorOnboardingSerializer):
    """Create a CAMPUS_MENTOR row (org.org_type must be 'College')."""

    def validate(self, attrs):
        attrs["mentor_tier"] = UserMentor.MentorTier.CAMPUS_MENTOR
        return attrs


class OrgMentorProfileUpdateSerializer(serializers.ModelSerializer):
    """Partial update of org-mentor own profile (about/expertise/reason only)."""

    class Meta:
        model = UserMentor
        fields = ["about", "expertise", "reason", "updated_by"]
        extra_kwargs = {
            "updated_by": {"required": True},
            "about":      {"required": False, "allow_null": True},
            "expertise":  {"required": False, "allow_null": True},
            "reason":     {"required": False, "allow_null": True},
        }


class OrgMentorListSerializer(serializers.ModelSerializer):
    """Read org-mentor profile for list and detail views."""

    full_name        = serializers.CharField(source="user.full_name")
    email            = serializers.EmailField(source="user.email")
    muid             = serializers.CharField(source="user.muid")
    profile_pic      = serializers.SerializerMethodField()
    org_name         = serializers.SerializerMethodField()
    org_type         = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = UserMentor
        fields = [
            "id", "full_name", "email", "muid", "profile_pic",
            "about", "expertise", "reason", "hours",
            "mentor_tier", "is_verified",
            "org_id", "org_name", "org_type",
            "verified_by_name", "verified_at", "verification_note",
            "created_at",
        ]

    def get_profile_pic(self, obj):
        return obj.user.profile_pic

    def get_org_name(self, obj):
        return obj.org.org_name if obj.org else None

    def get_org_type(self, obj):
        return obj.org.org_type if obj.org else None

    def get_verified_by_name(self, obj):
        return obj.verified_by.full_name if obj.verified_by else None


class OrgScopedSessionCreateSerializer(serializers.ModelSerializer):
    """Create a session scoped to a Company/Campus org.
    org is required; ig is optional (campus sessions may also link an IG chapter).
    Org-scoped sessions are auto-SCHEDULED — no admin approval queue."""

    class Meta:
        model = MentorshipSession
        fields = [
            "org", "ig",
            "title", "description", "mode",
            "starts_at", "ends_at",
            "meeting_link", "venue",
            "max_participants", "status",
            "created_by", "updated_by",
        ]
        extra_kwargs = {
            "org":              {"required": True},
            "ig":               {"required": False, "allow_null": True},
            "status":           {"required": False},
            "venue":            {"required": False, "allow_null": True},
            "meeting_link":     {"required": False, "allow_null": True},
            "max_participants": {"required": False, "allow_null": True},
            "created_by":       {"required": True},
            "updated_by":       {"required": True},
        }

    def validate(self, attrs):
        from utils.utils import DateTimeUtils
        starts_at = attrs.get("starts_at")
        ends_at   = attrs.get("ends_at")
        now       = DateTimeUtils.get_current_utc_time()

        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError("starts_at must be before ends_at.")
        if starts_at and starts_at < now:
            raise serializers.ValidationError("starts_at cannot be in the past.")

        mode         = attrs.get("mode", MentorshipSession.Mode.ONLINE)
        venue        = attrs.get("venue")
        meeting_link = attrs.get("meeting_link")

        if mode == MentorshipSession.Mode.ONLINE and not meeting_link:
            raise serializers.ValidationError({"meeting_link": "Meeting link required for ONLINE sessions."})
        if mode == MentorshipSession.Mode.OFFLINE and not venue:
            raise serializers.ValidationError({"venue": "Venue required for OFFLINE sessions."})
        if mode == MentorshipSession.Mode.HYBRID and not (meeting_link or venue):
            raise serializers.ValidationError("At least one of meeting_link or venue is required.")

        # Org-scoped sessions skip the admin approval queue
        attrs.setdefault("status", MentorshipSession.Status.SCHEDULED)
        attrs["is_global"] = False
        return attrs


class OrgOpportunitySerializer(serializers.ModelSerializer):
    """Read an org-scoped opportunity."""

    org_name        = serializers.SerializerMethodField()
    ig_name         = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.full_name")

    class Meta:
        model = IgOpportunity
        fields = [
            "id", "org_id", "org_name",
            "ig_id", "ig_name",
            "type", "title", "description",
            "eligibility", "application_url",
            "starts_at", "ends_at", "status",
            "created_by_name", "created_at", "updated_at",
        ]

    def get_org_name(self, obj):
        return obj.org.org_name if obj.org else None

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None


class OrgOpportunityWriteSerializer(serializers.ModelSerializer):
    """Create / update an org-scoped opportunity."""

    class Meta:
        model = IgOpportunity
        fields = [
            "org", "ig",
            "type", "title", "description",
            "eligibility", "application_url",
            "starts_at", "ends_at", "status",
            "created_by", "updated_by",
        ]
        extra_kwargs = {
            "org":              {"required": True},
            "ig":               {"required": False, "allow_null": True},
            "eligibility":      {"required": False, "allow_null": True},
            "application_url":  {"required": False, "allow_null": True},
            "starts_at":        {"required": False, "allow_null": True},
            "ends_at":          {"required": False, "allow_null": True},
            "status":           {"required": False},
            "created_by":       {"required": True},
            "updated_by":       {"required": True},
        }

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at   = attrs.get("ends_at",   getattr(self.instance, "ends_at",   None))
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError("starts_at must be before ends_at.")
        return attrs
