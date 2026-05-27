from django.utils import timezone
from rest_framework import serializers

from db.company import CompanyJob, CompanyJobApplication
from db.user import User


# ---------------------------------------------------------------------------
# Learner: Apply to a job
# ---------------------------------------------------------------------------

class ApplicationCreateSerializer(serializers.Serializer):
    """Validates the payload when a learner submits an application."""
    cover_note = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True,
        allow_null=True,
    )


# ---------------------------------------------------------------------------
# Learner: List own applications
# ---------------------------------------------------------------------------

class LearnerApplicationListSerializer(serializers.ModelSerializer):
    """Learner-facing view of their own application — includes job & company context."""
    job_id       = serializers.SerializerMethodField()
    job_title    = serializers.SerializerMethodField()
    job_type     = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    company_id   = serializers.SerializerMethodField()

    class Meta:
        model  = CompanyJobApplication
        fields = [
            'id', 'status', 'cover_note',
            'job_id', 'job_title', 'job_type', 'company_name', 'company_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_job_id(self, obj):
        return str(obj.job.id)

    def get_job_title(self, obj):
        return obj.job.title

    def get_job_type(self, obj):
        return obj.job.job_type

    def get_company_name(self, obj):
        return obj.job.company_id.name   # company_id is the FK name on CompanyJob

    def get_company_id(self, obj):
        return str(obj.job.company_id.id)


# ---------------------------------------------------------------------------
# Company: List applicants for a job
# ---------------------------------------------------------------------------

class ApplicantDetailSerializer(serializers.ModelSerializer):
    """Company-facing snapshot of a single applicant and their application state."""
    applicant_id   = serializers.SerializerMethodField()
    full_name      = serializers.SerializerMethodField()
    muid           = serializers.SerializerMethodField()
    district       = serializers.SerializerMethodField()
    karma          = serializers.SerializerMethodField()
    level          = serializers.SerializerMethodField()
    reviewed_by_id = serializers.SerializerMethodField()

    class Meta:
        model  = CompanyJobApplication
        fields = [
            'id', 'status', 'cover_note',
            'applicant_id', 'full_name', 'muid', 'district',
            'karma', 'level',
            'reviewed_by_id', 'reviewed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_applicant_id(self, obj):
        return str(obj.applicant.id)

    def get_full_name(self, obj):
        return obj.applicant.full_name

    def get_muid(self, obj):
        return obj.applicant.muid

    def get_district(self, obj):
        return obj.applicant.district.name if obj.applicant.district else None

    def get_karma(self, obj):
        wallet = getattr(obj.applicant, 'wallet_user', None)
        return wallet.karma if wallet else 0

    def get_level(self, obj):
        lvl_link = getattr(obj.applicant, 'user_lvl_link_user', None)
        if lvl_link is None:
            return None
        return {
            'id':          str(lvl_link.level.id),
            'name':        lvl_link.level.name,
            'level_order': lvl_link.level.level_order,
        }

    def get_reviewed_by_id(self, obj):
        return str(obj.reviewed_by.id) if obj.reviewed_by else None


# ---------------------------------------------------------------------------
# Company: Update application status
# ---------------------------------------------------------------------------

class ApplicationStatusUpdateSerializer(serializers.Serializer):
    """
    Validates a company's status-change request and enforces the FSM:
        applied     → shortlisted | rejected
        shortlisted → accepted    | rejected
        accepted    → (terminal)
        rejected    → (terminal)
        withdrawn   → (terminal)
    """
    status = serializers.ChoiceField(
        choices=[s[0] for s in CompanyJobApplication.STATUS_CHOICES]
    )

    def validate(self, attrs):
        new_status = attrs['status']
        # `self.context['current_status']` is injected by the view
        current_status = self.context.get('current_status')

        allowed = CompanyJobApplication.VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            if not allowed:
                raise serializers.ValidationError(
                    f"Status '{current_status}' is terminal — no further transitions allowed."
                )
            raise serializers.ValidationError(
                f"Cannot transition from '{current_status}' to '{new_status}'. "
                f"Allowed: {allowed}."
            )
        return attrs
