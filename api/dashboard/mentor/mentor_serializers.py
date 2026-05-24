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


class MentorOnboardingUpdateSerializer(serializers.ModelSerializer):
    """Partial update of mentor's own profile fields."""

    class Meta:
        model = UserMentor
        fields = ["about", "expertise", "reason", "preferred_ig_ids", "updated_by"]
        extra_kwargs = {
            "updated_by": {"required": True},
            "preferred_ig_ids": {"required": False},
        }


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
            "status",
            "is_global",
            "ig_id",
            "ig_name",
            "created_by_name",
            "created_at",
            "participant_count",
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
            "is_global",
            "status",
            "created_by",
            "updated_by",
        ]
        extra_kwargs = {
            "ig": {"required": False, "allow_null": True},
            "is_global": {"required": False},
            "status": {"required": False},
            "created_by": {"required": True},
            "updated_by": {"required": True},
        }


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
            "updated_by",
        ]
        extra_kwargs = {"updated_by": {"required": True}}


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


class MentorTaskRequestReviewSerializer(serializers.ModelSerializer):
    """Admin approves or rejects a mentor task request."""

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
