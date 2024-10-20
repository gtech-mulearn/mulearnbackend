import uuid

from django.db import models

from db.task import InterestGroup, KarmaActivityLog, Organization, TaskList
from db.user import User
from utils.utils import generate_code
from django.conf import settings

# fmt: off
# noinspection PyPep8

class LearningCircle(models.Model):
    id         = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()))
    name = models.CharField(max_length=255, unique=True)
    circle_code = models.CharField(unique=True, max_length=36)
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, blank=True,
                           related_name="learning_circle_ig")
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True,
                            related_name="learning_circle_org")
    meet_place = models.CharField(max_length=255, blank=True, null=True)
    meet_time = models.CharField(max_length=10, blank=True, null=True)
    day = models.CharField(max_length=20, blank=True, null=True)
    note = models.CharField(max_length=500, blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="learning_circle_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="learning_circle_created_by")
    created_at = models.DateTimeField(auto_now=True)

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
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()), unique=True)
    meet_code = models.CharField(max_length=6, default=generate_code,null=False,blank=False)
    circle = models.ForeignKey(LearningCircle, on_delete=models.CASCADE,
                               related_name='circle_meeting_log_learning_circle')
    title = models.CharField(max_length=100, null=False, blank=False)
    meet_time = models.DateTimeField(null=True, blank=False)
    meet_place = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=200, blank=False, null=False)
    day = models.CharField(max_length=20, null=True, blank=False)
    agenda = models.CharField(max_length=2000)
    pre_requirements = models.CharField(max_length=1000,null=True,blank=True)
    is_public = models.BooleanField(default=True, null=False)
    max_attendees = models.IntegerField(default=-1, null=False, blank=False)
    is_online = models.BooleanField(default=False, null=False)
    report_text = models.CharField(max_length=1000, null=True, blank=True)
    is_verified = models.BooleanField(default=False, null=False)
    is_started = models.BooleanField(default=False, null=False)
    is_report_submitted = models.BooleanField(default=False, null=False)
    images = models.ImageField(max_length=200, upload_to='lc/meet-report')
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='circle_meeting_log_created_by')
    created_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='circle_meeting_log_updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'circle_meeting_log'

class CircleMeetAttendees(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()), unique=True)
    meet = models.ForeignKey(CircleMeetingLog, on_delete=models.CASCADE, related_name='circle_meet_attendees_meet')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='circle_meet_attendees_user')
    note = models.CharField(max_length=1000, blank=True, null=True)
    is_report_submitted = models.BooleanField(default=False, null=False)
    report = models.CharField(max_length=500, null=True, blank=True)
    lc_member_rating = models.IntegerField(null=True)
    kal = models.ForeignKey(KarmaActivityLog,on_delete=models.SET_NULL, related_name="circle_meet_attendees_kal", null=True)
    karma_given = models.IntegerField(null=True)
    joined_at = models.DateTimeField(null=True, blank=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='approved_by',
                                   related_name='circle_meet_attendees_approved_by')
    created_at = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'circle_meet_attendees'

class CircleMeetTasks(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()), unique=True)
    meet = models.ForeignKey(CircleMeetingLog, null=True, on_delete=models.CASCADE, related_name="circle_meet_tasks_meet")
    title = models.CharField(max_length=100, null=False,blank=False)
    description = models.CharField(max_length=500, null=True)
    task = models.ForeignKey(TaskList, on_delete=models.CASCADE, related_name="circle_meet_tasks_task")
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'circle_meet_tasks'

class CircleMeetAttendeeReport(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=lambda: str(uuid.uuid4()), unique=True)
    meet_task = models.ForeignKey(CircleMeetTasks, on_delete=models.CASCADE, related_name="circle_meet_attendee_report_meet_task")
    attendee = models.ForeignKey(CircleMeetAttendees, on_delete=models.CASCADE, related_name="circle_meet_attendee_report_attendee")
    is_image = models.BooleanField(default=False,null=False,blank=False)
    image_url = models.ImageField(max_length=300,upload_to="lc/meet-report/attendee/")
    proof_url = models.URLField(max_length=300, null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'circle_meet_attendee_report'
