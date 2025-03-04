import uuid

from django.db import models

from db.task import InterestGroup, KarmaActivityLog, Organization, TaskList
from db.user import User
from utils.utils import generate_code
from django.conf import settings

# fmt: off
# noinspection PyPep8

class LearningCircle(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name="learning_circle_ig_id")
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="learning_circle_org_id", null=True, blank=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    title = models.CharField(max_length=100, blank=False, null=False)
    is_recurring = models.BooleanField(default=True, null=False)
    recurrence_type = models.CharField(max_length=10, blank=True, null=True)
    recurrence = models.IntegerField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="learning_circle_created_by")
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "learning_circle"

class UserCircleLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_circle_link_user')
    circle = models.ForeignKey(LearningCircle, on_delete=models.CASCADE, related_name='user_circle_link_circle')
    lead = models.BooleanField(default=False)
    is_invited = models.BooleanField(default=False)
    accepted = models.BooleanField()
    accepted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "user_circle_link"

class CircleMeetingLog(models.Model):
    MODE_CHOICES = (
        ("online", "Online"),
        ("offline", "Offline"),
    )
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    circle_id = models.ForeignKey(LearningCircle, on_delete=models.CASCADE, db_column="circle_id", related_name="circle_meeting_log_circle_id")
    meet_code = models.CharField(max_length=10, blank=True, null=True)
    title = models.CharField(max_length=100, blank=False, null=False)
    description = models.CharField(max_length=1000, blank=False, null=False)
    mode = models.CharField(max_length=10, blank=False, null=False, choices=MODE_CHOICES)
    is_report_needed = models.BooleanField(default=True, null=False)
    report_description = models.CharField(max_length=1000, blank=True, null=True)
    coord_x = models.FloatField(blank=False, null=False)
    coord_y = models.FloatField(blank=False, null=False)
    meet_place = models.CharField(max_length=100, blank=False, null=False)
    meet_link = models.CharField(max_length=200, blank=True, null=True)
    meet_time = models.DateTimeField(blank=False, null=False)
    duration = models.IntegerField(blank=False, null=False) 
    is_report_submitted = models.BooleanField(default=False, null=False)
    report_text = models.CharField(max_length=1000, blank=True, null=True)
    is_approved = models.BooleanField(default=False, null=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column="created_by", related_name="circle_meeting_log_created_by")
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "circle_meeting_log"


class CircleMeetingAttendees(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    meet_id = models.ForeignKey(CircleMeetingLog, on_delete=models.CASCADE, db_column="meet_id", related_name="circle_meeting_attendance_meet_id")
    user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id", related_name="circle_meeting_attendance_user_id")
    is_joined = models.BooleanField(default=False, null=False)
    joined_at = models.DateTimeField(blank=True, null=True)
    is_report_submitted = models.BooleanField(default=False, null=False)
    report_text = models.CharField(max_length=1000, blank=True, null=True)
    report_link = models.CharField(max_length=100, blank=True, null=True)
    is_lc_approved = models.BooleanField(default=False, null=False)
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "circle_meet_attendees"
