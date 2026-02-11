import uuid
from django.db import models
from django.conf import settings
from .user import User
from .organization import Organization


class Company(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='company_organization', blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='company_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='company_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'company'


class CompanyAdmin(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_admin_company')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='company_admin_user')
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='company_admin_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='company_admin_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'company_admin'
        unique_together = ('company', 'user')


class CompanyJob(models.Model):
    JOB_TYPE_CHOICES = [
        ('Hybrid', 'Hybrid'),
        ('Full-Time', 'Full-Time'),
        ('Remote', 'Remote'),
        ('Part-Time', 'Part-Time'),
        ('Internship', 'Internship'),
        ('Gig', 'Gig'),
    ]

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='company_job_company')
    title = models.CharField(max_length=75)
    experience = models.CharField(max_length=50, blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    salary_range = models.CharField(max_length=50, blank=True, null=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    min_karma = models.IntegerField(default=0)
    min_level = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='company_job_updated_by')
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='company_job_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'company_job'