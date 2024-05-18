from django.db import models
from db.user import User
from django.conf import settings
import uuid

class Project(models.Model):
    id = models.CharField(max_length=36, primary_key=True,default=uuid.uuid4)
    logo = models.ImageField(upload_to='project_logos/')
    description = models.TextField()
    project_image = models.ImageField(upload_to='project_images/')
    link = models.CharField(max_length=200)
    members = models.ManyToManyField(User, through='ProjectMembers', related_name='projects')
    created_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='project_created_by')
    updated_at = models.DateTimeField()
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by', related_name='project_updated_by')

    class Meta:
        managed = False
        db_table = 'project'

class ProjectCommandLink(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    command = models.TextField()
    project_id = models.CharField(max_length=36)
    user_id = models.CharField(max_length=36)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='command_created_by')
    updated_by = models.CharField(max_length=36)

    class Meta:
        managed = False
        db_table = 'project_command_link'

class ProjectVote(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    vote = models.CharField(max_length=8, choices=[('upvote', 'Upvote'), ('downvote', 'Downvote')])
    project_id = models.CharField(max_length=36)
    user_id = models.CharField(max_length=36)
    created_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='vote_created_by')

    class Meta:
        managed = False
        db_table = 'project_vote'
        

class ProjectMembers(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'project_members'
        unique_together = ('project', 'user')
