from django.db import models
from db.user import User
from db.task import InterestGroup , Organization
import uuid

class LearningCircle(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=255)
    circle_code = models.CharField(unique=True, max_length=36)
    ig =  models.ForeignKey(InterestGroup, on_delete=models.CASCADE, blank=True, null=True)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    meet_place = models.CharField(max_length=255, blank=True, null=True)
    meet_time = models.DateTimeField(blank=True, null=True)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, db_column='updated_by', related_name='learning_circle_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, models.DO_NOTHING, db_column='created_by', related_name='learning_circle_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'learning_circle'

class UserCircleLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, models.DO_NOTHING)
    circle = models.ForeignKey(LearningCircle, models.DO_NOTHING)
    lead_id = models.CharField(max_length=36)
    accepted = models.IntegerField()
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'user_circle_link'