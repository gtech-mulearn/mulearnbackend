import uuid

from django.core.files.storage import FileSystemStorage
from django.db import models
from decouple import config as decouple_config

from db.organization import Organization

from django.conf import settings
from .user import User

# fmt: off
# noinspection PyPep8


class Channel(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75, unique=True)
    discord_id = models.CharField(max_length=36)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="updated_by",
        related_name="channel_updated_by",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET(settings.SYSTEM_ADMIN_ID),
        db_column="created_by",
        related_name="channel_created_by",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "channel"


class InterestGroup(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75, unique=True)
    code = models.CharField(max_length=10, unique=True)
    # Legacy short emoji/code icon, superseded by the icon_image file upload
    # below. Kept nullable for backward compatibility with existing rows.
    icon = models.CharField(max_length=10, blank=True, null=True)
    category =models.CharField(max_length=20,default="others",blank=False,null=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('active', 'Active'),
            ('inactive', 'Inactive'),
            ('requested', 'Requested'),
            ('cancelled', 'Cancelled'),
            ('rejected', 'Rejected'),
        ],
        default='requested',
        blank=False,
        null=False
    )
    # PRD §7.3 — company-sponsored IG branding/framing: a company can request
    # to be the recognised sponsor of an IG, subject to platform-admin
    # approval. sponsor_status is independent of `status` above (which
    # governs the IG's own existence, not its sponsorship).
    sponsor_company = models.ForeignKey(
        'db.Company', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='sponsor_company_id', related_name='sponsored_igs'
    )
    sponsor_status = models.CharField(
        max_length=10, null=True, blank=True,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
    )
    about = models.TextField(blank=True, null=True)
    prerequisites = models.TextField(blank=True, null=True)
    career_opportunities = models.TextField(blank=True, null=True)
    top_blogs = models.TextField(blank=True, null=True)
    people_to_follow = models.TextField(blank=True, null=True)
    resource = models.TextField(blank=True, null=True)
    leads = models.TextField(blank=True, null=True)
    mentors = models.TextField(blank=True, null=True)
    thinktank = models.TextField(blank=True, null=True)
    office_hours = models.CharField(max_length=200, blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="interest_group_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="interest_group_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "interest_group"

    @property
    def cover_image(self):
        fs = FileSystemStorage()
        path = f"interest_group/cover/{self.id}.png"
        if fs.exists(path):
            return f"{decouple_config('BE_DOMAIN_NAME')}{fs.url(path)}"

    @property
    def icon_image(self):
        fs = FileSystemStorage()
        path = f"interest_group/icon/{self.id}.png"
        if fs.exists(path):
            return f"{decouple_config('BE_DOMAIN_NAME')}{fs.url(path)}"


class Level(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    level_order = models.IntegerField()
    name = models.CharField(max_length=36)
    karma = models.IntegerField()
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="level_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="level_updated_by")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "level"


class UserLvlLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="user_lvl_link_user")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="user_lvl_link_level")
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="user_lvl_link_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="user_lvl_link_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "user_lvl_link"


class TaskType(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="task_type_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="task_type_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "task_type"


class TaskList(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    hashtag = models.CharField(max_length=75)
    discord_link = models.CharField(max_length=200, blank=True, null=True)
    title = models.CharField(max_length=75)
    description = models.TextField(null=True, blank=True)
    karma = models.IntegerField(null=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, null=True)
    type = models.ForeignKey(TaskType, on_delete=models.CASCADE)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, null=True)
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, null=True, related_name="task_list_ig")
    event = models.CharField(max_length=50, null=True)
    event_fk = models.ForeignKey("db.Event", on_delete=models.SET_NULL, null=True, blank=True, db_column="event_id",
                                 related_name="task_list_events")
    active = models.BooleanField(default=True)
    variable_karma = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=1)
    bonus_time = models.DateTimeField(blank=True, null=True)
    bonus_karma = models.IntegerField(blank=True, null=True)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column="updated_by", related_name="task_list_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column="created_by", related_name="task_list_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    # Company task submission & admin approval workflow
    APPROVAL_STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('pending',  'Pending'),
        ('rejected', 'Rejected'),
        # PRD §6.3 — lightweight "request changes" state distinct from
        # outright rejection; the submitter can amend and resubmit.
        ('changes_requested', 'Changes Requested'),
    ]
    approval_status = models.CharField(
        max_length=20, choices=APPROVAL_STATUS_CHOICES, default='approved'
    )
    submitted_by_company = models.ForeignKey(
        'db.Company', on_delete=models.SET_NULL,
        null=True, blank=True, db_column='submitted_by_company_id',
        related_name='company_submitted_tasks'
    )
    rejection_reason = models.TextField(null=True, blank=True)
    reviewed_by_admin = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='reviewed_by_admin_id', related_name='task_list_reviewed_by'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Mentor task submission tracking
    requested_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='requested_by', related_name='task_list_requested_by'
    )
    requested_at = models.DateTimeField(null=True, blank=True)

    # Soft-delete tracking, distinct from `active` (which is used for the
    # pending-approval workflow and admin activation/deactivation toggle).
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='deleted_by', related_name='task_list_deleted_by'
    )

    class Meta:
        managed = False
        db_table = "task_list"
        indexes = [
            models.Index(fields=['event_fk'], name='idx_task_list_event_id'),
            models.Index(fields=['is_deleted'], name='idx_task_list_is_deleted'),
        ]


class Wallet(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet_user")
    karma = models.IntegerField(default=0)
    karma_last_updated_at = models.DateTimeField(blank=True, null=True, auto_now=True)
    coin = models.FloatField(default=0)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="wallet_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="wallet_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "wallet"


class KarmaActivityLog(models.Model):
    id = models.CharField(default=uuid.uuid4, primary_key=True, max_length=36)
    karma = models.IntegerField()
    task = models.ForeignKey(TaskList, on_delete=models.CASCADE, related_name="karma_activity_log_task")
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True,
                             related_name="karma_activity_log_user")
    task_message_id = models.CharField(max_length=36, blank=True, null=True)
    lobby_message_id = models.CharField(max_length=36, blank=True, null=True)
    dm_message_id = models.CharField(max_length=36, blank=True, null=True)
    peer_approved = models.BooleanField(blank=True, null=True)
    peer_approved_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="peer_approved_by", blank=True,
                                         null=True, related_name="karma_activity_log_peer_approved_by")
    appraiser_approved = models.BooleanField(blank=True, null=True)
    appraiser_approved_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="appraiser_approved_by",
                                                  blank=True, null=True,
                                              related_name="karma_activity_log_appraiser_approved_by")
    mentor_review_status = models.CharField(max_length=10, default='PENDING')
    mentor_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, db_column="mentor_reviewed_by",
                                           blank=True, null=True,
                                           related_name="karma_activity_log_mentor_reviewed_by")
    mentor_reviewed_at = models.DateTimeField(blank=True, null=True)
    mentor_review_feedback = models.CharField(max_length=500, blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="karma_activity_log_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="karma_activity_log_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "karma_activity_log"


class MucoinActivityLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mucoin_activity_log_user")
    coin = models.FloatField()
    status = models.CharField(max_length=36)
    task = models.ForeignKey(TaskList, on_delete=models.CASCADE, related_name="mucoin_activity_log_task_list")
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="mucoin_activity_log_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="mucoin_activity_log_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "mucoin_activity_log"


class MucoinInviteLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mucoin_invite_log_user")
    email = models.CharField(max_length=200)
    invite_code = models.CharField(max_length=36)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="mucoin_invite_log_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "mucoin_invite_log"


class UserIgLink(models.Model):

    class AssignmentType(models.TextChoices):
        MENTOR = 'MENTOR', 'Mentor'
        LEARNER = 'LEARNER', 'Learner'
        LEAD = 'LEAD', 'Lead'
        MODERATOR = 'MODERATOR', 'Moderator'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_ig_link_user")
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name="user_ig_link_ig")
    assignment_type = models.CharField(
        max_length=15, choices=AssignmentType.choices, default=AssignmentType.LEARNER
    )
    is_active = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        db_column='assigned_by', related_name='user_ig_link_assigned_by'
    )
    unassigned_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="user_ig_link_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    unassigned_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = "user_ig_link"


class UserIgLvlLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_ig_lvl_link_user")
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name="user_ig_lvl_link_ig")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="user_ig_lvl_link_level")
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="user_ig_lvl_link_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="user_ig_lvl_link_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "user_ig_lvl_link"
        unique_together = [("user", "ig")]


class UserIgLvlLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_ig_lvl_log_user")
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name="user_ig_lvl_log_ig")
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name="user_ig_lvl_log_level")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "user_ig_lvl_log"


class VoucherLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    code = models.CharField(unique=True, max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="voucher_log_user")
    task = models.ForeignKey(TaskList, on_delete=models.CASCADE, related_name="voucher_log_task")
    karma = models.IntegerField()
    week = models.CharField(max_length=2, null=True)
    month = models.CharField(max_length=10)
    claimed = models.BooleanField()
    event = models.CharField(max_length=50, null=True)
    description = models.CharField(max_length=2000, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="voucher_log_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="voucher_log_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "voucher_log"

class Category(models.Model):
    class EntityType(models.TextChoices):
        EVENT = 'event', 'Event'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    entity_id = models.CharField(max_length=36)
    entity_type = models.CharField(max_length=20, choices=EntityType.choices)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="category_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="category_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed = False
        db_table = "categories"
        indexes = [
            models.Index(fields=['entity_id', 'entity_type'], name='idx_categories_entity'),
        ]


class TaskReport(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name="task_report_reporter")
    offender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="task_report_offender")
    message_id = models.CharField(max_length=100)
    reason = models.CharField(max_length=500)
    proof_link = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, default="PENDING")
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by", related_name="task_report_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by", related_name="task_report_updated_by")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "task_report"




