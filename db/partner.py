import uuid
from django.db import models


class UserPartner(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    user_link = models.OneToOneField(
        'User',
        on_delete=models.CASCADE,
        related_name='partner_profile',
    )
    name = models.CharField(max_length=255, unique=True)
    slug = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, default='pending')
    rejection_reason = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    email = models.CharField(max_length=100)
    logo = models.TextField(null=True, blank=True)
    short_pitch = models.CharField(max_length=900, null=True, blank=True)
    location = models.CharField(max_length=150, null=True, blank=True)
    district = models.ForeignKey(
        'District',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='partners',
        db_column='district_id',
    )
    state = models.ForeignKey(
        'State',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='partners_state',
        db_column='state_id',
    )
    country = models.ForeignKey(
        'Country',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='partners_country',
        db_column='country_id',
    )
    partner_type = models.CharField(max_length=75, null=True, blank=True)
    website_link = models.TextField(null=True, blank=True)
    social_links = models.JSONField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=36, null=True, blank=True)
    updated_by = models.CharField(max_length=36, null=True, blank=True)
    verified_by = models.CharField(max_length=36, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'user_partner'
