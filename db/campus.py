import uuid

from django.db import models

from .user import User
from .organization import Organization
from .task import InterestGroup

# fmt: off
# noinspection PyPep8


class CampusIGChapter(models.Model):
    """Campus-level chapter of a global Interest Group.

    One IG can have at most one chapter per campus (enforced by unique_together).
    """
    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    org         = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='campus_ig_chapters')
    ig          = models.ForeignKey(InterestGroup, on_delete=models.CASCADE, related_name='campus_chapters')
    lead_user   = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    db_column='lead_user_id', related_name='led_campus_ig_chapters')
    is_active   = models.BooleanField(default=True)
    created_by  = models.ForeignKey(User, on_delete=models.RESTRICT,
                                    db_column='created_by', related_name='created_campus_ig_chapters')
    created_at  = models.DateTimeField()
    updated_by  = models.ForeignKey(User, on_delete=models.RESTRICT,
                                    db_column='updated_by', related_name='updated_campus_ig_chapters')
    updated_at  = models.DateTimeField()

    class Meta:
        managed         = False
        db_table        = 'campus_ig_chapter'
        unique_together = (('org', 'ig'),)


class CampusSocialLink(models.Model):
    """Social media / web presence URL for a campus.

    One row per (campus, platform) pair. Platform is unique per campus.
    """
    PLATFORM_CHOICES = [
        ('instagram', 'Instagram'), ('linkedin',  'LinkedIn'),
        ('twitter',   'Twitter'),   ('youtube',   'YouTube'),
        ('website',   'Website'),   ('facebook',  'Facebook'),
        ('github',    'GitHub'),    ('other',     'Other'),
    ]

    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    org         = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='social_links')
    platform    = models.CharField(max_length=30, choices=PLATFORM_CHOICES)
    url         = models.URLField(max_length=500)
    label       = models.CharField(max_length=100, null=True, blank=True)
    created_by  = models.ForeignKey(User, on_delete=models.RESTRICT,
                                    db_column='created_by', related_name='created_campus_social_links')
    created_at  = models.DateTimeField()
    updated_by  = models.ForeignKey(User, on_delete=models.RESTRICT,
                                    db_column='updated_by', related_name='updated_campus_social_links')
    updated_at  = models.DateTimeField()

    class Meta:
        managed         = False
        db_table        = 'campus_social_link'
        unique_together = (('org', 'platform'),)


class CampusExecomRole(models.Model):
    """Admin-defined campus execom role (e.g. Chairperson, Tech Lead).

    These are governance titles — separate from system permission roles.
    Admins create the master list; campus leads assign members.
    """
    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    title       = models.CharField(max_length=100, unique=True)
    priority    = models.IntegerField(default=0)
    is_active   = models.BooleanField(default=True)
    created_by  = models.ForeignKey(User, on_delete=models.RESTRICT,
                                    db_column='created_by', related_name='created_campus_execom_roles')
    created_at  = models.DateTimeField()
    updated_by  = models.ForeignKey(User, on_delete=models.RESTRICT,
                                    db_column='updated_by', related_name='updated_campus_execom_roles')
    updated_at  = models.DateTimeField()

    class Meta:
        managed  = False
        db_table = 'campus_execom_role'

    def __str__(self):
        return self.title


class CampusExecom(models.Model):
    """Campus-level assignment of a user to an execom role.

    A user may hold multiple roles; each (org, user, role) tuple is unique.
    """
    id          = models.CharField(primary_key=True, max_length=36, default=uuid.uuid4)
    org         = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='campus_execom_members')
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campus_execom_links')
    role        = models.ForeignKey(CampusExecomRole, on_delete=models.CASCADE, related_name='execom_assignments')
    created_by  = models.ForeignKey(User, on_delete=models.RESTRICT,
                                    db_column='created_by', related_name='created_campus_execom')
    created_at  = models.DateTimeField()

    class Meta:
        managed         = False
        db_table        = 'campus_execom'
        unique_together = (('org', 'user', 'role'),)
