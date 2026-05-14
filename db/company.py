import uuid
from django.db import models
from django.conf import settings
from .user import User
from .skill import Skill             # import the Skill model
from .task import InterestGroup  # import InterestGroup model
from .achievement import Achievement

class Company(models.Model):
    STATUS_CHOICES = [
        ('pending_verification', 'Pending Verification'),
        ('active', 'Active'),
        ('rejected', 'Rejected'),
        ('inactive', 'Inactive'),
        ('blocked', 'Blocked'),
    ]

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company_user_id = models.ForeignKey(User, on_delete=models.CASCADE, db_column='company_user_id', related_name='company_user')
    name = models.CharField(max_length=75, unique=True)
    logo = models.TextField(blank=True, null=True)
    description = models.TextField()
    industry_sector = models.CharField(max_length=75, blank=True, null=True)
    website_link = models.TextField(blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    slug = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    legal_name = models.CharField(max_length=150, blank=True, null=True)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    tax_id = models.CharField(max_length=100, blank=True, null=True)
    company_size = models.CharField(max_length=50, blank=True, null=True)
    linkedin_url = models.TextField(blank=True, null=True)
    verification_document_url = models.TextField(blank=True, null=True)
    founded_year = models.PositiveSmallIntegerField(blank=True, null=True)
    remote_policy = models.CharField(max_length=20, blank=True, null=True)
    culture_text = models.TextField(blank=True, null=True)
    tech_stack = models.JSONField(blank=True, null=True)
    perks = models.JSONField(blank=True, null=True)
    testimonials = models.JSONField(blank=True, null=True)
    gallery = models.JSONField(blank=True, null=True)
    verification_requested_at = models.DateTimeField(blank=True, null=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verified_by = models.CharField(max_length=36, blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    updated_by = models.CharField(max_length=36, blank=True, null=True)
    deleted_by = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'company'


class CompanyJob(models.Model):
    JOB_TYPE_CHOICES = [
        ('Hybrid', 'Hybrid'),
        ('Full-Time', 'Full-Time'),
        ('Remote', 'Remote'),
        ('Part-Time', 'Part-Time'),
        ('Internship', 'Internship'),
        ('Gig', 'Gig'),
    ]

    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Active', 'Active'),
        ('Closed', 'Closed'),
        ('Expired', 'Expired'),
    ]

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company_id = models.ForeignKey(Company, on_delete=models.CASCADE, db_column='company_id', related_name='company_jobs')
    title = models.CharField(max_length=75)
    experience = models.CharField(max_length=20, blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=75, blank=True, null=True)
    salary_range = models.CharField(max_length=36, blank=True, null=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    is_deleted = models.BooleanField(default=False)
    min_karma = models.IntegerField(blank=True, null=True)
    min_level = models.SmallIntegerField(blank=True, null=True)  # TINYINT

    # --- Job Enhancement Fields ---
    # Applicable to all job types (display only, no automatic karma crediting)
    karma_reward = models.IntegerField(blank=True, null=True)

    # Applicable to Gig and Internship types
    DURATION_UNIT_CHOICES = [
        ('days',   'Days'),
        ('weeks',  'Weeks'),
        ('months', 'Months'),
    ]
    duration_value = models.PositiveSmallIntegerField(blank=True, null=True)
    duration_unit  = models.CharField(
        max_length=10, choices=DURATION_UNIT_CHOICES, blank=True, null=True
    )

    # Applicable to Gig type only
    hourly_rate  = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    deliverables = models.JSONField(blank=True, null=True)  # list of strings

    # Applicable to Internship type only
    stipend              = models.CharField(max_length=75, blank=True, null=True)
    certificate_provided = models.BooleanField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_jobs'

class CompanyJobRule(models.Model):
    RULE_CHOICES = [
        ('skill', 'Skill'),
        ('interest_group', 'Interest Group'),
        ('achievement', 'Achievement')
    ]
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    job = models.ForeignKey(CompanyJob,  related_name="rules",  on_delete=models.CASCADE)
    rule_type = models.CharField(max_length=20, choices=RULE_CHOICES)
    rule_type_id = models.CharField(max_length=36)  # generic FK
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
     
        db_table = "company_job_rules"
        unique_together = ('job', 'rule_type', 'rule_type_id')

    @property
    def rule_detail(self):
        if self.rule_type == 'skill':
            return Skill.objects.get(id=self.rule_type_id)
        elif self.rule_type == 'interest_group':
            return InterestGroup.objects.get(id=self.rule_type_id)
        else:
            return Achievement.objects.get(id=self.rule_type_id)


class CompanyJobApplication(models.Model):
    """
    Tracks a learner's application to a CompanyJob.

    Status workflow:
        applied → shortlisted → accepted  (terminal)
                ↘            ↘ rejected   (terminal)
                  → rejected
        withdrawn — set by learner (terminal)
    """

    STATUS_CHOICES = [
        ('applied',     'Applied'),
        ('shortlisted', 'Shortlisted'),
        ('accepted',    'Accepted'),
        ('rejected',    'Rejected'),
        ('withdrawn',   'Withdrawn'),
    ]

    # Allowed forward-transitions enforced at the API layer
    VALID_TRANSITIONS = {
        'applied':     ['shortlisted', 'rejected'],
        'shortlisted': ['accepted', 'rejected'],
        'accepted':    [],
        'rejected':    [],
        'withdrawn':   [],
    }

    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    job         = models.ForeignKey(
                      CompanyJob, on_delete=models.CASCADE,
                      related_name='applications', db_column='job_id')
    applicant   = models.ForeignKey(
                      User, on_delete=models.CASCADE,
                      related_name='company_job_applications', db_column='applicant_id')
    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default='applied')
    cover_note  = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
                      User, on_delete=models.SET_NULL,
                      null=True, blank=True,
                      related_name='reviewed_applications',
                      db_column='reviewed_by')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_job_applications'
        unique_together = [('job', 'applicant')]
