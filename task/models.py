from django.db import models
from user.models import User


# Create your models here.
class Channel(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    discord_id = models.CharField(max_length=36)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', related_name='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'channel'


class TaskType(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=75)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', related_name='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'task_type'


class TaskList(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    hashtag = models.CharField(max_length=75)
    title = models.CharField(max_length=75)
    description = models.CharField(max_length=200, blank=True, null=True)
    karma = models.IntegerField(blank=True, null=True)
    channel = models.ForeignKey(Channel, models.DO_NOTHING)
    type = models.ForeignKey(TaskType, models.DO_NOTHING)
    active = models.IntegerField()
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', related_name='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'task_list'


class TotalKarma(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.OneToOneField(User, models.DO_NOTHING)
    karma = models.BigIntegerField()
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', related_name='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'total_karma'


class KarmaActivityLog(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    karma = models.IntegerField()
    task = models.ForeignKey(TaskList, models.DO_NOTHING)
    task_message_id = models.CharField(max_length=36)
    lobby_message_id = models.CharField(max_length=36, blank=True, null=True)
    peer_approved = models.IntegerField(blank=True, null=True)
    appraiser_approved = models.IntegerField(blank=True, null=True)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', related_name='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'karma_activity_log'


class InterestGroup(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=75)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', related_name='updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'interest_group'


class UserIgLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    ig = models.ForeignKey(InterestGroup, models.DO_NOTHING)
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_ig_link'