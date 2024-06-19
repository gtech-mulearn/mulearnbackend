import uuid 

from django.db import models
from db.user import User
from django.conf import settings

class Project(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    logo = models.ImageField(upload_to='projects/logos/', null=True, blank=True)
    title = models.CharField(max_length=50, blank=False)
    description = models.CharField(max_length=200, blank=False)
    link = models.URLField()
    contributors = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='created_projects', db_column='created_by')
    # updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='updated_projects', db_column='updated_by')

    class Meta:
        managed = False
        db_table = "projects"
        ordering = ["created_at"]
    
class ProjectImage(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    project = models.ForeignKey(Project, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='projects/images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "project_images"
        
class Comment(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    comment = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='comments')
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)
    # created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='created_comments', db_column='created_by')
    updated_at = models.DateTimeField(auto_now=True)
    # updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='updated_comments', db_column='updated_by')

    class Meta:
        managed = False
        db_table = "projects_comments"
        ordering = ["created_at"]
        
class Vote(models.Model):
    VOTE_CHOICES = [('upvote', 'Upvote'), ('downvote', 'Downvote')]
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    vote = models.CharField(max_length=10, choices=VOTE_CHOICES)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='votes')
    # user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='votes')
    created_at = models.DateTimeField(auto_now_add=True)
    # created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='created_votes', db_column='created_by')
    updated_at = models.DateTimeField(auto_now=True)
    # updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), related_name='updated_votes', db_column='updated_by')

    class Meta:
        managed = False
        db_table = "projects_votes"
        ordering = ["created_at"]