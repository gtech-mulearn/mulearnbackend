"""
MentorTaskRequest model — stored in `mentor_task_request` table.

A mentor submits a request to create a new task/hashtag for their IG.
Admin reviews the queue, then APPROVES (creates the TaskList entry) or REJECTS.

This model is managed=False since it needs a matching migration/schema.
Run the provided ALTER script to create the table.
"""
import uuid
from django.db import models
from django.conf import settings
from db.user import User
from db.task import InterestGroup, TaskList


class MentorTaskRequest(models.Model):

    class Status(models.TextChoices):
        PENDING  = 'PENDING',  'Pending'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)

    mentor = models.ForeignKey(
        User, on_delete=models.CASCADE,
        db_column='mentor_id', related_name='mentor_task_requests'
    )
    ig = models.ForeignKey(
        InterestGroup, on_delete=models.CASCADE,
        db_column='ig_id', related_name='mentor_task_requests'
    )

    # Fields the mentor proposes — mirrors TaskList fields
    title    = models.CharField(max_length=75)
    hashtag  = models.CharField(max_length=75)
    karma    = models.IntegerField()
    description = models.TextField(blank=True, null=True)

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )

    # Populated by admin on approval/rejection
    admin_note = models.CharField(max_length=500, blank=True, null=True)
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='reviewed_by', related_name='mentor_task_request_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Set when approved — FK to the created TaskList row
    created_task = models.ForeignKey(
        TaskList, on_delete=models.SET_NULL,
        null=True, blank=True,
        db_column='created_task_id', related_name='mentor_task_request_source'
    )

    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='created_by', related_name='mentor_task_request_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column='updated_by', related_name='mentor_task_request_updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'mentor_task_request'
