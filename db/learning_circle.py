from django.db import models

from db.task import InterestGroup, Organization
from db.user import User
# fmt: off

class LearningCircle(models.Model):
    id         = models.CharField(primary_key=True, max_length=36)
    name       = models.CharField(max_length=255, unique=True)
    circle_code= models.CharField(unique=True, max_length=36)
    ig         = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, blank=True, null=True)
    org        = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    meet_place = models.CharField(max_length=255, blank=True, null=True)
    meet_time  = models.CharField(max_length=10, blank=True, null=True)
    day        = models.CharField(max_length=20, blank=True, null=True)
    note       = models.CharField(max_length=500, blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column="updated_by", related_name="learning_circle_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column="created_by", related_name="learning_circle_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "learning_circle"


class UserCircleLink(models.Model):
    id         = models.CharField(primary_key=True, max_length=36)
    user       = models.ForeignKey(User, on_delete=models.CASCADE)
    circle     = models.ForeignKey(LearningCircle, on_delete=models.CASCADE)
    lead       = models.BooleanField(default=False)
    is_invited = models.BooleanField(default=False)
    accepted   = models.BooleanField()
    accepted_at= models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "user_circle_link"