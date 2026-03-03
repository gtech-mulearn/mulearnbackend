import uuid
from django.db import models
from .user import User
from .skill import Skill
from .task import InterestGroup
from .achievement import Achievement


class Company(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("inactive", "Inactive"),
    ]

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company_user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        db_column="company_user_id",
        related_name="company_user",
    )
    name = models.CharField(max_length=75, unique=True)
    logo = models.TextField(blank=True, null=True)
    description = models.TextField()
    industry_sector = models.CharField(max_length=75, blank=True, null=True)
    website_link = models.TextField(blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    slug = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    location = models.CharField(max_length=150, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    # DB uses VARCHAR(36), not FK
    updated_by = models.CharField(max_length=36, blank=True, null=True)
    deleted_by = models.CharField(max_length=36, blank=True, null=True)

    class Meta:
        managed = False
        db_table = "company"

    def __str__(self):
        return self.name


class CompanyJob(models.Model):
    JOB_TYPE_CHOICES = [
        ("Hybrid", "Hybrid"),
        ("Full-Time", "Full-Time"),
        ("Remote", "Remote"),
        ("Part-Time", "Part-Time"),
        ("Internship", "Internship"),
        ("Gig", "Gig"),
    ]

    STATUS_CHOICES = [
        ("Draft", "Draft"),
        ("Active", "Active"),
        ("Closed", "Closed"),
        ("Expired", "Expired"),
    ]

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    company_id = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        db_column="company_id",
        related_name="company_jobs",
    )
    title = models.CharField(max_length=75)
    experience = models.CharField(max_length=20, blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=75, blank=True, null=True)
    salary_range = models.CharField(max_length=36, blank=True, null=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="Draft")
    is_deleted = models.BooleanField(default=False)
    min_karma = models.IntegerField(blank=True, null=True)
    min_level = models.SmallIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "company_jobs"


class CompanyJobRule(models.Model):
    RULE_CHOICES = [
        ("skill", "Skill"),
        ("interest_group", "Interest Group"),
        ("achievement", "Achievement"),
    ]

    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    job = models.ForeignKey(CompanyJob, related_name="rules", on_delete=models.CASCADE)
    rule_type = models.CharField(max_length=20, choices=RULE_CHOICES)
    rule_type_id = models.CharField(max_length=36)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "company_job_rules"
        unique_together = ("job", "rule_type", "rule_type_id")

    @property
    def rule_detail(self):
        if self.rule_type == "skill":
            return Skill.objects.get(id=self.rule_type_id)
        elif self.rule_type == "interest_group":
            return InterestGroup.objects.get(id=self.rule_type_id)
        else:
            return Achievement.objects.get(id=self.rule_type_id)
