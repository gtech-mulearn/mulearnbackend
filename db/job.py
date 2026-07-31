import uuid
from django.db import models

class CompanyJob(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey('db.Company', on_delete=models.CASCADE, related_name='jobs')
    created_by = models.ForeignKey('db.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='company_jobs_created', db_column='created_by')
    title = models.CharField(max_length=75)
    experience = models.CharField(max_length=20, null=True, blank=True)
    job_description = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=75, null=True, blank=True)
    salary_range = models.CharField(max_length=36, null=True, blank=True)
    job_type = models.CharField(max_length=20) # Enum: Hybrid, Full-Time, Remote, Part-Time, Internship, Gig
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default='Draft') # Enum: Draft, Active, Closed, Expired, Pending Approval, Rejected
    approved_by = models.ForeignKey('db.User', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='company_jobs_approved', db_column='approved_by')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)
    duration_value = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_unit = models.CharField(max_length=20, null=True, blank=True) # Enum: days, weeks, months
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    deliverables = models.JSONField(null=True, blank=True)
    stipend = models.CharField(max_length=75, null=True, blank=True)
    certificate_provided = models.CharField(max_length=3, null=True, blank=True) # Enum: Yes, No
    total_views = models.IntegerField(default=0)
    expires_at = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey('db.User', on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='company_jobs_updated', db_column='updated_by')

    class Meta:
        managed = False
        db_table = 'company_jobs'

class CompanyJobRule(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    job = models.ForeignKey(CompanyJob, on_delete=models.CASCADE, related_name='rules')
    rule_type = models.CharField(max_length=50) # min_karma, max_karma, min_level, max_level, skill, degree, etc.
    rule_value = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_job_rules'

class UserJobApplication(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    job = models.ForeignKey(CompanyJob, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey('db.User', on_delete=models.CASCADE, related_name='company_job_applications')
    resume_link = models.TextField(null=True, blank=True)
    cover_letter = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, default='Pending') # Pending, In-Review, Shortlisted, Interview, Rejected, Selected
    rejection_reason = models.TextField(null=True, blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'user_job_application'
        unique_together = ('job', 'user')
