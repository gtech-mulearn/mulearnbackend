import uuid

from django.db import models

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
    icon = models.CharField(max_length=10)
    category =models.CharField(max_length=20,default="others",blank=False,null=False)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="interest_group_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="interest_group_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "interest_group"


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
    description = models.CharField(max_length=200, null=True)
    karma = models.IntegerField(null=True)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, null=True)
    type = models.ForeignKey(TaskType, on_delete=models.CASCADE)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, null=True)
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, null=True, related_name="task_list_ig")
    event = models.CharField(max_length=50, null=True)
    active = models.BooleanField(default=True)
    variable_karma = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=1)
    bonus_time = models.DateTimeField(blank=True, null=True)
    bonus_karma = models.IntegerField(blank=True, null=True)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column="updated_by", related_name="task_list_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column="created_by", related_name="task_list_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "task_list"


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
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_ig_link_user")
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name="user_ig_link_ig")
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="user_ig_link_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "user_ig_link"


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


class Events(models.Model):
    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name        = models.CharField(max_length=75)
    description = models.CharField(max_length=200, null=True)
    updated_by  = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by", related_name="event_updated_by")
    updated_at  = models.DateTimeField(auto_now=True)
    created_by  = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by", related_name="event_created_by")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "events"
