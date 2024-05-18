import uuid
from django.db import models
from db.user import User




class Project(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    logo = models.URLField(blank=True, null=True)
    description = models.TextField()
    link = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, models.DO_NOTHING, related_name='project_created_by', db_column="created_by")
    updated_at = models.DateTimeField(blank=True, null=True, auto_now=True)
    updated_by = models.ForeignKey(User, models.DO_NOTHING, related_name="project_updated_by", db_column="updated_by")

    class Meta:
        managed=False
        db_table = 'project'


class ProjectUpvote(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, models.SET_NULL, null=True, db_column="user")
    project = models.ForeignKey(Project, models.CASCADE, db_column="project", related_name="project_upvote")

    class Meta:
        managed=False
        db_table = 'project_upvote'


class ProjectImages(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    image = models.URLField()
    project = models.ForeignKey(Project, models.CASCADE, db_column="project", related_name="project_image")

    class Meta:
        managed=False
        db_table = 'project_image'


class ProjectContributorsLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user = models.ForeignKey(User, models.CASCADE, related_name='project_contributed', db_column="user")
    project = models.ForeignKey(Project, models.CASCADE, related_name='project_contributor', db_column="project")

    class Meta:
        managed=False
        db_table = 'project_contributor_link'