import uuid
from django.db import models

class Company(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company_user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='company_profile')
    org = models.ForeignKey('Organization', on_delete=models.SET_NULL, null=True, blank=True, related_name='companies')
    name = models.CharField(max_length=75, unique=True)
    logo = models.TextField(null=True, blank=True)
    description = models.TextField()
    short_pitch = models.CharField(max_length=900, null=True, blank=True)
    industry_sector = models.CharField(max_length=75, null=True, blank=True)
    website_link = models.TextField(null=True, blank=True)
    email = models.CharField(max_length=100, null=True, blank=True)
    slug = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, default="pending")
    location = models.CharField(max_length=150, null=True, blank=True)
    district = models.ForeignKey('District', on_delete=models.SET_NULL, null=True, blank=True, related_name='companies')
    state = models.ForeignKey('State', on_delete=models.SET_NULL, null=True, blank=True, related_name='companies_state')
    country = models.ForeignKey('Country', on_delete=models.SET_NULL, null=True, blank=True, related_name='companies_country')
    legal_name = models.CharField(max_length=150, null=True, blank=True)
    registration_number = models.CharField(max_length=100, null=True, blank=True)
    tax_id = models.CharField(max_length=100, null=True, blank=True)
    company_size = models.CharField(max_length=50, null=True, blank=True)
    linkedin_url = models.TextField(null=True, blank=True)
    verification_document_url = models.TextField(null=True, blank=True)
    verification_requested_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.CharField(max_length=36, null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.CharField(max_length=36, null=True, blank=True)
    deleted_by = models.CharField(max_length=36, null=True, blank=True)
    founded_year = models.PositiveSmallIntegerField(null=True, blank=True)
    remote_policy = models.CharField(max_length=20, null=True, blank=True)
    culture_text = models.TextField(null=True, blank=True)
    tech_stack = models.JSONField(null=True, blank=True)
    perks = models.JSONField(null=True, blank=True)
    testimonials = models.JSONField(null=True, blank=True)
    gallery = models.JSONField(null=True, blank=True)
    # PRD §13.3 — company opt-in to show a summarized Impact Report on its
    # public profile as a trust/marketing signal. Default False: impact data
    # is only ever public if the company deliberately chooses to publish it.
    publish_impact_report = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'company'


class CompanyAdminLink(models.Model):
    class Status(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        ACCEPTED = 'Accepted', 'Accepted'
        DECLINED = 'Declined', 'Declined'
        REVOKED = 'Revoked', 'Revoked'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id', related_name='admin_links')
    user = models.ForeignKey('User', on_delete=models.CASCADE, db_column='user_id', related_name='company_admin_links')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    invited_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, db_column='invited_by_id', related_name='company_admin_links_invited_by')
    invited_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, db_column='revoked_by_id', related_name='company_admin_links_revoked_by')
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('User', on_delete=models.CASCADE, db_column='created_by', related_name='company_admin_links_created_by')
    updated_by = models.ForeignKey('User', on_delete=models.CASCADE, db_column='updated_by', related_name='company_admin_links_updated_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_admin_link'
        unique_together = ('company', 'user')


class CompanyTalentShortlist(models.Model):
    """
    PRD §11.3 — a company's bookmarked-candidate pipeline, independent of any
    formal job application. Mirrors the ComicBookmarkLink pattern
    (db/comic.py) — a plain (company, user) bookmark with an optional note.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        db_column='company_id', related_name='talent_shortlist_links'
    )
    user = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='user_id', related_name='company_shortlist_links'
    )
    note = models.CharField(max_length=500, blank=True, null=True)
    created_by = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='created_by', related_name='company_talent_shortlist_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'company_talent_shortlist'
        unique_together = [('company', 'user')]


class CompanyFeedback(models.Model):
    """
    PRD §13 — structured feedback captured at each interaction-completion
    point (job outcome, task completion, event attendance, mentorship
    session), rolled up into the company's Impact Report. `entity_id` is a
    polymorphic pointer whose type depends on `interaction_type` (a
    CompanyJob id, TaskList id, Event id, or MentorshipSession id) — the same
    pattern EventConnection already uses for its own polymorphic entity_id.
    """

    class InteractionType(models.TextChoices):
        JOB = 'JOB', 'Job Application'
        TASK = 'TASK', 'Task Completion'
        EVENT = 'EVENT', 'Event Attendance'
        SESSION = 'SESSION', 'Mentorship Session'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        db_column='company_id', related_name='feedback_entries'
    )
    interaction_type = models.CharField(max_length=10, choices=InteractionType.choices)
    entity_id = models.CharField(max_length=36)
    submitted_by = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='submitted_by', related_name='company_feedback_submitted'
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'company_feedback'
        unique_together = [('company', 'interaction_type', 'entity_id', 'submitted_by')]


class Collaboration(models.Model):
    """
    PRD §10.3 — a discoverable propose/accept entity that sits in front of
    the existing EventConnection mechanism, not a replacement of it. A
    company posts an intent (open discovery, or a direct invite to a
    specific campus/IG); the target expresses interest/accepts/declines.
    If `event` is set, acceptance auto-creates the matching EventConnection
    collaborator row so no duplicate data model exists for "this is now an
    event" — Collaboration is purely about discovery and proposal.
    """

    class CollabType(models.TextChoices):
        EVENT_COHOST = 'EVENT_COHOST', 'Event Co-host'
        IG_SPONSORSHIP = 'IG_SPONSORSHIP', 'IG Sponsorship'
        CAMPUS_PARTNERSHIP = 'CAMPUS_PARTNERSHIP', 'Campus Partnership'
        MENTORSHIP_EXCHANGE = 'MENTORSHIP_EXCHANGE', 'Mentorship Exchange'

    class TargetType(models.TextChoices):
        IG = 'IG', 'Interest Group'
        CAMPUS = 'CAMPUS', 'Campus'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'          # discovery post, no specific target yet
        PENDING = 'PENDING', 'Pending'  # directly invited a specific target
        ACCEPTED = 'ACCEPTED', 'Accepted'
        DECLINED = 'DECLINED', 'Declined'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        db_column='company_id', related_name='collaborations'
    )
    collab_type = models.CharField(max_length=25, choices=CollabType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    # target_type/target_org_id null together = open discovery post, not yet
    # aimed at a specific campus/IG. Set together = a direct invite.
    target_type = models.CharField(max_length=10, choices=TargetType.choices, blank=True, null=True)
    target_org_id = models.CharField(max_length=36, blank=True, null=True)
    # Optional: if this collaboration is about co-hosting a specific
    # already-created event, acceptance auto-wires an EventConnection here.
    event = models.ForeignKey(
        'Event', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='event_id', related_name='collaboration_proposals'
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)
    responded_by = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='responded_by', related_name='collaboration_responses'
    )
    responded_at = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.CharField(max_length=500, blank=True, null=True)
    created_by = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='created_by', related_name='collaboration_created_by'
    )
    updated_by = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='updated_by', related_name='collaboration_updated_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_collaboration'


class CompanyTaskTemplate(models.Model):
    """
    PRD §6.3 — reusable structure for recurring company task types (e.g. a
    monthly challenge), so a company doesn't re-key the same fields every
    time. A template is copied into a normal TaskList row at creation time
    via the company task-creation endpoint; it has no life of its own beyond
    being a prefill source.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        db_column='company_id', related_name='task_templates'
    )
    title = models.CharField(max_length=75)
    hashtag_prefix = models.CharField(max_length=75, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    karma = models.IntegerField(blank=True, null=True)
    type = models.ForeignKey(
        'TaskType', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='type_id', related_name='company_task_templates'
    )
    created_by = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='created_by', related_name='company_task_template_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_task_template'


class CompanyEventTemplate(models.Model):
    """PRD §8.3 — reusable structure for recurring company event types (recruiting webinar, tech talk, hackathon)."""
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        db_column='company_id', related_name='event_templates'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)
    default_duration_minutes = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(
        'User', on_delete=models.CASCADE,
        db_column='created_by', related_name='company_event_template_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_event_template'
