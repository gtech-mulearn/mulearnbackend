import uuid
from django.db import models


class Hiring(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    posted_date = models.DateField(null=True, blank=True)
    role = models.CharField(max_length=255)
    organization = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    lastdate = models.DateField(db_index=True)
    applylink = models.URLField(null=True, blank=True)
    jdlink = models.URLField(null=True, blank=True)
    duration = models.CharField(max_length=100, null=True, blank=True)
    remuneration = models.CharField(max_length=255, null=True, blank=True)
    vacancies = models.PositiveIntegerField(null=True, blank=True)
    extracontent = models.TextField(null=True, blank=True)
    created_by = models.ForeignKey(
        'db.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='hiring_created_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        'db.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='hiring_updated_by'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'hiring'
