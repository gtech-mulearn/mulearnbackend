import uuid

from django.db import models

from db.organization import Organization
from .user import User


class Channel(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    discord_id = models.CharField(max_length=36)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="updated_by",
        related_name="channel_updated_by",
    )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="channel_created_by",
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "channel"


class InterestGroup(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=75, unique=True)
    code = models.CharField(max_length=10, unique=True)
    icon = models.CharField(max_length=10, unique=True)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="updated_by",
        related_name="interest_group_updated_by",
    )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="interest_group_created_by",
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "interest_group"


class Level(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    level_order = models.IntegerField()
    name = models.CharField(max_length=36)
    karma = models.IntegerField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="level_created_by",
    )
    created_at = models.DateTimeField()
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="updated_by",
        related_name="level_updated_by",
    )
    updated_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "level"


class UserLvlLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    level = models.ForeignKey(Level, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="updated_by",
        related_name="user_lvl_link_updated_by",
    )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="user_lvl_link_created_by",
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "user_lvl_link"


class TaskType(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="updated_by",
        related_name="task_type_updated_by",
    )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="task_type_created_by",
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "task_type"


class TaskList(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    hashtag = models.CharField(max_length=75)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=200, blank=True, null=True)
    karma = models.IntegerField(blank=True, null=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE)
    type = models.ForeignKey(TaskType, on_delete=models.CASCADE)
    org = models.ForeignKey(
        Organization, on_delete=models.CASCADE, blank=True, null=True
    )
    level = models.ForeignKey(Level, on_delete=models.CASCADE, blank=True, null=True)
    ig = models.ForeignKey(
        InterestGroup, on_delete=models.CASCADE, blank=True, null=True
    )
    active = models.BooleanField()
    variable_karma = models.BooleanField()
    usage_count = models.IntegerField(blank=True, null=True)
    updated_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        db_column="updated_by",
        related_name="task_list_updated_by",
    )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        db_column="created_by",
        related_name="task_list_created_by",
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "task_list"


class TotalKarma(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="total_karma_user"
    )
    karma = models.IntegerField()
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="updated_by",
        related_name="total_karma_updated_by",
    )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="total_karma_created_by",
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "total_karma"


class KarmaActivityLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    karma = models.IntegerField()
    task = models.ForeignKey(TaskList, on_delete=models.CASCADE)
    task_message_id = models.CharField(max_length=36)
    lobby_message_id = models.CharField(max_length=36, blank=True, null=True)
    dm_message_id = models.CharField(max_length=36, blank=True, null=True)
    peer_approved = models.BooleanField(blank=True, null=True)
    peer_approved_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="peer_approved_by",
        blank=True,
        null=True,
        related_name="karma_activity_log_peer_approved_by",
    )
    appraiser_approved = models.BooleanField(blank=True, null=True)
    appraiser_approved_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="appraiser_approved_by",
        blank=True,
        null=True,
        related_name="karma_activity_log_appraiser_approved_by",
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="updated_by",
        related_name="karma_activity_log_updated_by",
    )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="karma_activity_log_created_by",
    )
    created_at = models.DateTimeField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="karma_activity_log_user",
    )

    class Meta:
        managed = False
        db_table = "karma_activity_log"


class UserIgLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_ig_link_user"
    )
    ig = models.ForeignKey(
        InterestGroup, on_delete=models.CASCADE, related_name="user_ig_link_ig"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="created_by",
        related_name="user_ig_link_created_by",
    )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "user_ig_link"


class VoucherLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    code = models.CharField(unique=True, max_length=255)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='voucher_log_user'
        )
    task = models.ForeignKey(
        TaskList, 
        on_delete=models.CASCADE, 
        related_name='voucher_log_task'
        )
    karma = models.IntegerField()
    mail = models.CharField(max_length=255)
    week = models.CharField(max_length=2)
    month = models.CharField(max_length=10)
    claimed = models.BooleanField()
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='updated_by', 
        related_name='voucher_log_updated_by'
        )
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        db_column='created_by', 
        related_name='voucher_log_created_by'
        )
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'voucher_log'