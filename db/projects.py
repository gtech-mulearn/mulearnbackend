from django.db import models
from db.user import User
from django.conf import settings

class Projects(models.Model):
    id                = models.CharField(max_length=36, primary_key=True)
    logo              = models.CharField(max_length=255, null=True, blank=True)
    description       = models.TextField()
    project_image     = models.CharField(max_length=255, null=True, blank=True)
    link              = models.URLField(max_length=255, null=True, blank=True)
    contributors      = models.TextField(null=True, blank=True)
    updated_by        = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by', related_name='project_updated_by')
    updated_at        = models.DateTimeField(auto_now=True)
    created_by        = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='project_created_by')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed       = False
        db_table      = 'projects'

class ProjectsCommandLink(models.Model):
    id                = models.CharField(max_length=36, primary_key=True)
    command           = models.TextField()
    project           = models.ForeignKey(Project, on_delete=models.CASCADE)
    user              = models.ForeignKey(User, on_delete=models.CASCADE)
    updated_by        = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by', related_name='command_updated_by')
    updated_at        = models.DateTimeField(auto_now=True)
    created_by        = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='command_created_by')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed       = False
        db_table      = 'ProjectsCommandLink'

class ProjectsUpvoteLink(models.Model):
    VOTE_CHOICES = [
        ('upvote', 'Upvote'),
        ('downvote', 'Downvote')
    ]

    id                = models.CharField(max_length=36, primary_key=True)
    vote              = models.CharField(max_length=7, choices=VOTE_CHOICES)
    project           = models.ForeignKey(Project, on_delete=models.CASCADE)
    user              = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at        = models.DateTimeField(auto_now_add=True)
    created_by        = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='upvotes_created_by')

    class Meta:
        managed       = False
        db_table      = 'ProjectsUpvoteLink'
