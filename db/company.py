import uuid
from django.db import models
from django.conf import settings
from .user import User


class Company(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, blank=True, null=True)
    location = models.CharField(max_length=150, blank=True, null=True)
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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Draft')
    is_deleted = models.BooleanField(default=False)
    min_karma = models.IntegerField(blank=True, null=True)
    min_level = models.SmallIntegerField(blank=True, null=True)  # TINYINT
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'company_jobs'