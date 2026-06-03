import uuid

from django.db import models
from django.conf import settings

from .user import User
from .task import InterestGroup

# fmt: off
# noinspection PyPep8


class MentorAvailabilitySlot(models.Model):
    """
    Mentor's recurring weekly availability windows.
    ig_id is nullable: NULL means the slot is not tied to a specific IG
    and applies globally across all of the mentor's IGs.
    """

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    mentor_user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='mentor_user_id', related_name='availability_slots'
    )
    ig = models.ForeignKey(
        InterestGroup, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='ig_id',
        related_name='mentor_availability_slots'
    )
    # 1=Monday … 7=Sunday
    weekday = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=64, default='Asia/Kolkata')
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='avail_slot_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='avail_slot_updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'mentor_availability_slot'


class MentorshipSession(models.Model):

    class Mode(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        OFFLINE = 'OFFLINE', 'Offline'
        HYBRID = 'HYBRID', 'Hybrid'

    class Status(models.TextChoices):
        # Global sessions start here until an admin approves them
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        SCHEDULED        = 'SCHEDULED',        'Scheduled'
        COMPLETED        = 'COMPLETED',        'Completed'
        CANCELLED        = 'CANCELLED',        'Cancelled'
        REJECTED         = 'REJECTED',         'Rejected'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    ig = models.ForeignKey(
        InterestGroup, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='ig_id',
        related_name='mentorship_sessions'
    )
    title = models.CharField(max_length=150)
    description = models.TextField(null=True, blank=True)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.ONLINE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    meeting_link = models.CharField(max_length=500, null=True, blank=True)
    venue = models.CharField(max_length=255, null=True, blank=True)
    max_participants = models.IntegerField(null=True, blank=True)
    # is_global=True when ig is NULL and the session was submitted by a mentor
    # for cross-IG or platform-wide reach; requires admin approval.
    is_global = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        # IG sessions default to SCHEDULED; global sessions default to PENDING_APPROVAL
        default=Status.SCHEDULED,
    )
    # Populated by admin when approving or rejecting a global session
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='approved_by', related_name='mentorship_session_approved_by'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='mentorship_session_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='mentorship_session_updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    # Org-scoped sessions (COMPANY_MENTOR / CAMPUS_MENTOR).
    # NULL for global and IG-scoped sessions.
    org = models.ForeignKey(
        'db.Organization',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='org_id',
        related_name='mentorship_sessions'
    )

    class Meta:
        managed = False
        db_table = 'mentorship_session'


class MentorshipSessionUserLink(models.Model):

    class ParticipantRole(models.TextChoices):
        MENTOR = 'MENTOR', 'Mentor'
        MENTEE = 'MENTEE', 'Mentee'
        CO_MENTOR = 'CO_MENTOR', 'Co-Mentor'

    class AttendanceStatus(models.TextChoices):
        INVITED = 'INVITED', 'Invited'
        ATTENDED = 'ATTENDED', 'Attended'
        ABSENT = 'ABSENT', 'Absent'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    session = models.ForeignKey(
        MentorshipSession, on_delete=models.CASCADE,
        db_column='session_id', related_name='participants'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='user_id', related_name='session_participations'
    )
    participant_role = models.CharField(max_length=10, choices=ParticipantRole.choices)
    attendance_status = models.CharField(
        max_length=10, choices=AttendanceStatus.choices, default=AttendanceStatus.INVITED
    )
    progress_note = models.CharField(max_length=500, null=True, blank=True)
    contributed_minutes = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'mentorship_session_user_link'
        unique_together = [('session', 'user', 'participant_role')]


class IgOpportunity(models.Model):

    class OpportunityType(models.TextChoices):
        CHALLENGE = 'CHALLENGE', 'Challenge'
        INTERNSHIP = 'INTERNSHIP', 'Internship'
        HACKATHON = 'HACKATHON', 'Hackathon'
        JOB = 'JOB', 'Job'

    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        PUBLISHED = 'PUBLISHED', 'Published'
        CLOSED = 'CLOSED', 'Closed'
        ARCHIVED = 'ARCHIVED', 'Archived'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    ig = models.ForeignKey(
        InterestGroup, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='ig_id', related_name='ig_opportunities'
    )
    # Org-scoped opportunity (COMPANY_MENTOR / CAMPUS_MENTOR).
    # Either ig or org must be set; both can be set for campus+IG opps.
    org = models.ForeignKey(
        'db.Organization',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='org_id',
        related_name='org_opportunities'
    )
    type = models.CharField(max_length=15, choices=OpportunityType.choices)
    title = models.CharField(max_length=150)
    description = models.TextField()
    eligibility = models.TextField(null=True, blank=True)
    application_url = models.CharField(max_length=500, null=True, blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='ig_opportunity_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='ig_opportunity_updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'ig_opportunity'


class MentorKarmaAward(models.Model):
    """
    Tracks karma awarded by an admin to a mentor after a completed session.
    One award per (session, mentor) pair — enforced by unique_together.
    The kal_id FK is set after the KarmaActivityLog row is created.
    """
    id         = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    session    = models.ForeignKey(
        MentorshipSession, on_delete=models.CASCADE,
        db_column='session_id', related_name='karma_awards'
    )
    mentor     = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='mentor_id', related_name='mentor_karma_awards'
    )
    karma      = models.IntegerField()
    note       = models.CharField(max_length=500, null=True, blank=True)
    awarded_by = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='awarded_by', related_name='mentor_karma_awards_given'
    )
    awarded_at = models.DateTimeField()
    # Linked KarmaActivityLog row — set after KAL is created
    kal_id     = models.CharField(max_length=36, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'mentor_karma_award'
        unique_together = [('session', 'mentor')]


class SystemActionLog(models.Model):

    class ActionType(models.TextChoices):
        PERSONA_SWITCH   = 'PERSONA_SWITCH',   'Persona Switch'
        MENTOR_VERIFY    = 'MENTOR_VERIFY',    'Mentor Verify'
        TASK_REVIEW      = 'TASK_REVIEW',      'Task Review'
        EVENT_REVIEW     = 'EVENT_REVIEW',     'Event Review'
        SESSION_CREATE   = 'SESSION_CREATE',   'Session Create'
        SESSION_UPDATE   = 'SESSION_UPDATE',   'Session Update'
        SESSION_STATUS   = 'SESSION_STATUS',   'Session Status'
        KARMA_AWARD      = 'KARMA_AWARD',      'Karma Award'
        MANUAL_HOURS_LOG = 'MANUAL_HOURS_LOG', 'Manual Hours Log'
        IG_CONTENT_UPDATE = 'IG_CONTENT_UPDATE', 'IG Content Update'
        OPPORTUNITY_POST = 'OPPORTUNITY_POST', 'Opportunity Post'
        INTERN_TASK_UPDATE = 'INTERN_TASK_UPDATE', 'Intern Task Update'
        INTERN_LEAVE_REQUEST = 'INTERN_LEAVE_REQUEST', 'Intern Leave Request'
        INTERN_LEAVE_REVIEW = 'INTERN_LEAVE_REVIEW', 'Intern Leave Review'
        INTERN_TIMESHEET_EDIT = 'INTERN_TIMESHEET_EDIT', 'Intern Timesheet Edit'
        INTERN_GUILD_REASSIGN = 'INTERN_GUILD_REASSIGN', 'Intern Guild Reassign'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    action_type = models.CharField(max_length=25, choices=ActionType.choices)
    actor_user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='actor_user_id', related_name='system_actions_as_actor'
    )
    subject_user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='subject_user_id', related_name='system_actions_as_subject'
    )
    ig = models.ForeignKey(
        InterestGroup, on_delete=models.SET_NULL,
        null=True, blank=True, db_column='ig_id',
        related_name='system_action_logs'
    )
    # Generic entity reference (e.g. 'events', 'mentorship_session')
    entity_name = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=36)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    remarks = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'system_action_log'
