import uuid

from django.conf import settings
from django.db import models

from .task import InterestGroup
from .user import User


class CommunityPartner(models.Model):
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    name = models.CharField(max_length=150)
    logo_key = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    linkedin = models.CharField(max_length=255, blank=True, null=True)
    github = models.CharField(max_length=255, blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    instagram = models.CharField(max_length=255, blank=True, null=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
        related_name='community_partner_created_by',
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='updated_by',
        related_name='community_partner_updated_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'community_partner'


class IgCommunityPartnerLink(models.Model):
    """
    Links a CommunityPartner to an InterestGroup. A partner can be linked
    to multiple IGs; an IG can have multiple partners.
    """
    id = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    community_partner = models.ForeignKey(
        CommunityPartner, on_delete=models.CASCADE,
        db_column='community_partner_id', related_name='ig_links',
    )
    interest_group = models.ForeignKey(
        InterestGroup, on_delete=models.CASCADE,
        db_column='ig_id', related_name='community_partner_links',
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by',
        related_name='ig_community_partner_link_created_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'ig_community_partner_link'
        unique_together = [('community_partner', 'interest_group')]
