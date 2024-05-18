from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    logo = models.CharField(max_length=255, blank=True, null=True)  # URL or path to the logo image
    description = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    contributors = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.CharField(max_length=255)

class ProjectImage(models.Model):
    project = models.ForeignKey(Project, related_name='images', on_delete=models.CASCADE)
    image_url = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

class ProjectsCommand(models.Model):
    command = models.TextField()
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=255)
    updated_by = models.CharField(max_length=255)

class ProjectsUpvote(models.Model):
    VOTE_CHOICES = [
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote')
    ]
    vote = models.CharField(max_length=10, choices=VOTE_CHOICES)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255)
