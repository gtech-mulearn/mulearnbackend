import uuid
from django.db import models
from django.conf import settings
from .user import User


class Command(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    command = models.TextField()
    project_id = models.ForeignKey("Projects", on_delete=models.SET(settings.SYSTEM_ADMIN_ID))
    user_id = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255)
    updated_by = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'project_command'


class Vote(models.Model):
    VOTE_CHOICES = [
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote'),
    ]
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4())
    vote = models.CharField(max_length=8, choices=VOTE_CHOICES)
    project_id = models.ForeignKey("Projects", on_delete=models.SET(settings.SYSTEM_ADMIN_ID))
    user_id = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'project_vote'


class Projects(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=255)
    logo = models.ImageField(max_length=200, blank=True,null=True, upload_to='hackathon/project_logo')
    description = models.TextField()
    project_image = models.ForeignKey("ProjectImages",on_delete=models.CASCADE,related_name="projects", db_column="projects_image")
    link = models.URLField()
    contributors = models.ForeignKey("ProjectContributors",on_delete=models.CASCADE, related_name="projects", db_column="projects_contributors")
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by", related_name="projects_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by", related_name="projects_created_by")

    class Meta:
        managed = False
        db_table = 'projects'


class ProjectContributors(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'project_contributors'


class ProjectImages(models.Model):
    image = models.ImageField(max_length=200, blank=True, null=True, upload_to='hackathon/project_images')

    class Meta:
        managed = False
        db_table = 'project_images'
