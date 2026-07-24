import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models

from db.task import InterestGroup
from db.user import User
from decouple import config as decouple_config


class ImpactProject(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, db_column="ig_id",
                           related_name="impact_project_ig")
    title = models.CharField(max_length=200)
    description = models.TextField()
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="updated_by",
                                   related_name="impact_project_updated_by")
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column="created_by",
                                   related_name="impact_project_created_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "impact_project"

    @property
    def image(self):
        fs = FileSystemStorage()
        path = f"impact_project/image/{self.id}.png"
        if fs.exists(path):
            return f"{decouple_config('BE_DOMAIN_NAME')}{fs.url(path)}"


class ImpactProjectUserLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    project = models.ForeignKey(ImpactProject, on_delete=models.CASCADE, db_column="project_id",
                                related_name="impact_project_user_link_project")
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column="user_id",
                             related_name="impact_project_user_link_user")
    is_lead = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "impact_project_user_link"

class ImpactProjectLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    project = models.ForeignKey(ImpactProject, on_delete=models.CASCADE, db_column="project_id",
                                related_name="impact_project_link_project")
    label = models.CharField(max_length=50)
    url = models.URLField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "impact_project_link"