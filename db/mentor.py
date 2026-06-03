import uuid
from django.db import models
from django.conf import settings
from db.user import User
from db.task import InterestGroup

class MentorshipSession(models.Model):
    class Mode(models.TextChoices):
        ONLINE = 'ONLINE', 'Online'
        OFFLINE = 'OFFLINE', 'Offline'
        HYBRID = 'HYBRID', 'Hybrid'

    class Status(models.TextChoices):
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'
        REJECTED = 'REJECTED', 'Rejected'

    class SessionType(models.TextChoices):
        IG_SESSION      = 'ig_session',      'IG Session'
        CAMPUS_SESSION  = 'campus_session',  'Campus Session'
        COMPANY_SESSION = 'company_session', 'Company Session'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    session_type = models.CharField(max_length=20, choices=SessionType.choices, default=SessionType.IG_SESSION)
    entity_id = models.CharField(max_length=36, blank=True, null=True)
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, null=True)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.ONLINE)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    meeting_link = models.CharField(max_length=500, blank=True, null=True)
    venue = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    max_participants = models.IntegerField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column="created_by", related_name="mentorship_session_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column="updated_by", related_name="mentorship_session_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, db_column="approved_by", related_name="mentorship_session_approved_by")
    approved_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'mentorship_session'

class MentorAvailabilitySlot(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    mentor_user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="mentor_user_id", related_name="availability_slots")
    ig = models.ForeignKey(InterestGroup, on_delete=models.SET_NULL, null=True, db_column="ig_id", related_name="availability_slots")
    weekday = models.SmallIntegerField() # 1=Mon ... 7=Sun
    start_time = models.TimeField()
    end_time = models.TimeField()
    timezone = models.CharField(max_length=64, default="Asia/Kolkata")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(blank=True, null=True)
    valid_to = models.DateField(blank=True, null=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column="created_by", related_name="mentor_availability_slot_created_by")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column="updated_by", related_name="mentor_availability_slot_updated_by")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'mentor_availability_slot'

class MentorshipSessionUserLink(models.Model):
    class ParticipantRole(models.TextChoices):
        MENTOR = 'MENTOR', 'Mentor'
        MENTEE = 'MENTEE', 'Mentee'
        CO_MENTOR = 'CO_MENTOR', 'Co-Mentor'

    class AttendanceStatus(models.TextChoices):
        INVITED = 'INVITED', 'Invited'
        ATTENDED = 'ATTENDED', 'Attended'
        ABSENT = 'ABSENT', 'Absent'

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    session = models.ForeignKey(MentorshipSession, on_delete=models.CASCADE, db_column="session_id", related_name="participant_links")
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id", related_name="mentorship_session_links")
    participant_role = models.CharField(max_length=20, choices=ParticipantRole.choices)
    attendance_status = models.CharField(max_length=20, choices=AttendanceStatus.choices, default=AttendanceStatus.INVITED)
    progress_note = models.CharField(max_length=500, blank=True, null=True)
    feedback = models.TextField(blank=True, null=True)
    contributed_minutes = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'mentorship_session_user_link'
        unique_together = (('session', 'user', 'participant_role'),)
