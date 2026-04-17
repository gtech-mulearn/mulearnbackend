import uuid

from django.db import models

from django.conf import settings
from .user import User, Role
from .organization import Organization
from .task import InterestGroup

# fmt: off
# noinspection PyPep8


class CampusIGChapter(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='campus_ig_chapter_org')
    ig = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name='campus_ig_chapter_ig')
    lead = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='lead_id',
                             related_name='campus_ig_chapter_lead', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='campus_ig_chapter_created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='campus_ig_chapter_updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'campus_ig_chapter'


class CampusSocialLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='campus_social_link_org')
    platform = models.CharField(max_length=30)
    url = models.URLField(max_length=500)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='campus_social_link_created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='campus_social_link_updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'campus_social_link'


class CampusExecom(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    campus = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='campus_execom_campus'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campus_execom_user')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='campus_execom_role')
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
                                   related_name='campus_execom_created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
                                   related_name='campus_execom_updated_by')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'campus_execom'
        constraints = [
            models.UniqueConstraint(fields=['campus', 'role'], name='campus_execom_unique_role_per_campus')
        ]
