import uuid

from django.db import models
from django.conf import settings

from .user import User
from .company import Company


class ProblemStatement(models.Model):

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        CLOSED = 'closed', 'Closed'
        ARCHIVED = 'archived', 'Archived'
        REMOVED = 'removed', 'Removed'

    class Difficulty(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'

    class RewardType(models.TextChoices):
        CASH = 'cash', 'Cash Prize'
        JOB_INTERVIEW = 'job_interview', 'Job Interview'
        KARMA = 'karma', 'Karma Points'
        CERTIFICATE = 'certificate', 'Certificate'
        NONE = 'none', 'None'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE,
        db_column='company_id', related_name='problem_statements'
    )
    title = models.CharField(max_length=200)
    slug = models.CharField(max_length=220, unique=True, db_index=True)
    summary = models.CharField(max_length=500)
    description = models.TextField()
    categories = models.JSONField(blank=True, null=True)
    skills = models.JSONField(blank=True, null=True)
    requirements = models.TextField(blank=True, null=True)
    expected_outcome = models.TextField(blank=True, null=True)
    resources = models.JSONField(blank=True, null=True)
    cover_image = models.CharField(max_length=512, blank=True, null=True)

    difficulty = models.CharField(
        max_length=20, choices=Difficulty.choices, default=Difficulty.INTERMEDIATE
    )

    reward_type = models.CharField(
        max_length=50, choices=RewardType.choices, default=RewardType.NONE
    )
    reward_details = models.TextField(blank=True, null=True)
    contact_email = models.CharField(max_length=100, blank=True, null=True)
    external_link = models.CharField(max_length=500, blank=True, null=True)
    deadline = models.DateTimeField(blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT
    )
    removal_reason = models.CharField(max_length=500, blank=True, null=True)

    is_featured = models.BooleanField(default=False)
    view_count = models.PositiveIntegerField(default=0)
    interest_count = models.PositiveIntegerField(default=0)

    published_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    archived_at = models.DateTimeField(blank=True, null=True)

    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='problem_statement_created_by'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='problem_statement_updated_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    deleted_at = models.DateTimeField(blank=True, null=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='deleted_by', related_name='problem_statement_deleted_by'
    )

    class Meta:
        managed = False
        db_table = 'problem_statement'


class ProblemStatementInterest(models.Model):

    class Status(models.TextChoices):
        INTERESTED = 'interested', 'Interested'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    problem_statement = models.ForeignKey(
        ProblemStatement, on_delete=models.CASCADE,
        db_column='problem_statement_id', related_name='interests'
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='user_id', related_name='problem_statement_interests'
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INTERESTED
    )
    note = models.TextField(blank=True, null=True)
    work_link = models.CharField(max_length=500, blank=True, null=True)

    status_updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='status_updated_by', related_name='problem_statement_interest_status_updated_by'
    )
    status_updated_at = models.DateTimeField(auto_now=True)
    expressed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'problem_statement_interest'
        unique_together = [('problem_statement', 'user')]


class ProblemStatementAuditLog(models.Model):

    class Action(models.TextChoices):
        CREATED = 'CREATED', 'Created'
        UPDATED = 'UPDATED', 'Updated'
        PUBLISHED = 'PUBLISHED', 'Published'
        CLOSED = 'CLOSED', 'Closed'
        ARCHIVED = 'ARCHIVED', 'Archived'
        REMOVED = 'REMOVED', 'Removed'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    problem_statement = models.ForeignKey(
        ProblemStatement, on_delete=models.CASCADE,
        db_column='problem_statement_id', related_name='audit_logs'
    )
    target_type = models.CharField(max_length=50, default='problem_statement')
    target_id = models.CharField(max_length=36)
    action = models.CharField(max_length=50, choices=Action.choices)
    actor = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='actor_id', related_name='problem_statement_audit_logs_actor'
    )
    actor_role = models.CharField(max_length=50, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'problem_statement_audit_log'
