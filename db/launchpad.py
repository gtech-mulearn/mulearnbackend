from django.db import models
from django.conf import settings
from db.user import User
from db.organization import Organization

class LaunchpadCompanies(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=100, unique=True)
    website = models.URLField(max_length=200, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    poc_name = models.CharField(max_length=100)
    poc_role = models.CharField(max_length=100)
    poc_email = models.CharField(max_length=100)
    poc_phone = models.CharField(max_length=20)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'launchpad_companies'


class LaunchpadRecruiters(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    company = models.ForeignKey(
        LaunchpadCompanies,
        on_delete=models.CASCADE,
        db_column='company_id',
        related_name='recruiters'
    )
    name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, unique=True)
    phone = models.CharField(max_length=20)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'launchpad_recruiters'


class LaunchpadJobTasks(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    task_description = models.TextField()
    hashtags = models.CharField(max_length=255, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'launchpad_job_tasks'
        managed = False


class LaunchpadJobs(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    company = models.ForeignKey(
        LaunchpadCompanies,
        on_delete=models.CASCADE,
        db_column='company_id',
        related_name='jobs'
    )
    recruiter = models.ForeignKey(
        LaunchpadRecruiters,
        on_delete=models.CASCADE,
        db_column='recruiter_id',
        related_name='jobs'
    )
    title = models.CharField(max_length=100)
    skills = models.CharField(max_length=255, null=True, blank=True)
    opening_type = models.CharField(max_length=50, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    salary_range = models.CharField(max_length=50, null=True, blank=True)
    job_type = models.CharField(max_length=50, null=True, blank=True)
    minimum_karma = models.IntegerField(default=0,null=True, blank=True)
    experience = models.CharField(max_length=255, null=True, blank=True)
    domain = models.CharField(max_length=255)
    interest_groups = models.CharField(max_length=255)
    task = models.ForeignKey(
        LaunchpadJobTasks,
        on_delete=models.CASCADE,
        db_column='task_id',
        related_name='jobs'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'launchpad_jobs'
        managed = False
        
class LaunchpadJobApplications(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    job = models.ForeignKey(
        LaunchpadJobs,
        on_delete=models.CASCADE,
        db_column='job_id',
        related_name='applications'
    )
    student = models.ForeignKey(
        User,  # From your existing User model
        on_delete=models.CASCADE,
        db_column='student_id',
        related_name='job_applications'
    )
    
    # Application Status
    INVITATION_STATUS_CHOICES = [
        ('invited', 'Invited'),
        ('applied', 'Applied'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ]
    status = models.CharField(max_length=20, choices=INVITATION_STATUS_CHOICES, default='invited')
    
    # Application Form Fields
    resume_link = models.URLField(max_length=500, null=True, blank=True)
    linkedin_link = models.URLField(max_length=500, null=True, blank=True)
    portfolio_link = models.URLField(max_length=500, null=True, blank=True)
    cover_letter = models.TextField(null=True, blank=True)
    other_link = models.URLField(max_length=500, null=True, blank=True)
    
    interview_link = models.URLField(max_length=500, null=True, blank=True)
    interview_date = models.DateTimeField(null=True, blank=True)
    interview_time = models.TimeField(null=True, blank=True)
    interview_platform = models.CharField(max_length=255, null=True, blank=True)
    # Metadata
    invited_at = models.DateTimeField(auto_now_add=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'launchpad_job_applications'
        unique_together = ['job', 'student']
        managed = False
#<--------------------------------- old launchpad -------------------------------------->
class LaunchPadUsers(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    email = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=15, null=True)
    full_name = models.CharField(max_length=255, null=True)
    district = models.CharField(max_length=100, null=True)
    zone = models.CharField(max_length=100, null=True)
    role = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'launchpad_user'

    
class LaunchPadUserCollegeLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(LaunchPadUsers, on_delete=models.CASCADE, related_name="launchpaduserlink_user")
    college = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="launchpaduserlink_college")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(LaunchPadUsers, on_delete=models.CASCADE, related_name='launchpad_user_college_link_created_by')
    updated_by = models.ForeignKey(LaunchPadUsers, on_delete=models.CASCADE, related_name='launchpad_user_college_link_updated_by')

    class Meta:
        managed = False
        db_table = 'launchpad_user_college_link'

class LaunchPad(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name="launchpad_user")
    launchpad_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name="launchpad_created_by", db_column='created_by')
    updated_by = models.ForeignKey(User,on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name="launchpad_updated_by", db_column='updated_by')

    class Meta:
        managed = False
        db_table = 'launchpad'