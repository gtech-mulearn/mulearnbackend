from django.db import models

from db.organization import Organization, District
from db.user import User


class Hackathon(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    title = models.CharField(max_length=100)
    tagline = models.CharField(max_length=150, blank=True, null=True)
    description = models.CharField(max_length=5000, blank=True, null=True)
    participant_count = models.IntegerField(blank=True, null=True)
    type = models.CharField(max_length=8, default="offline")
    website = models.CharField(max_length=200, null=True, blank=True)
    org = models.ForeignKey(Organization, on_delete=models.CASCADE, blank=True, null=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    event_logo = models.CharField(max_length=200, blank=True, null=True)
    banner = models.CharField(max_length=200, blank=True, null=True)
    is_open_to_all = models.BooleanField(blank=True, null=True)
    application_start = models.DateTimeField(blank=True, null=True)
    application_ends = models.DateTimeField(blank=True, null=True)
    event_start = models.DateTimeField(blank=True, null=True)
    event_end = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='hackathon_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='hackathon_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'hackathon'


class HackathonForm(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    hackathon = models.ForeignKey(Hackathon, on_delete=models.CASCADE)
    field_name = models.CharField(max_length=255)
    field_type = models.CharField(max_length=50)
    is_required = models.BooleanField(default=False)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='hackathon_form_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='hackathon_form_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'hackathon_form'


class HackathonOrganiserLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    organiser = models.ForeignKey(User, on_delete=models.CASCADE)
    hackathon = models.ForeignKey(Hackathon, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='hackathon_organiser_link_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='hackathon_organiser_link_created_by')
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'hackathon_organiser_link'


class HackathonUserSubmission(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    hackathon = models.ForeignKey(Hackathon, on_delete=models.CASCADE)
    updated_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='updated_by',
                                   related_name='hackathon_submission_updated_by')
    updated_at = models.DateTimeField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, db_column='created_by',
                                   related_name='hackathon_submission_created_by')
    created_at = models.DateTimeField()
    data = models.CharField(max_length=2000, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'hackathon_submission'