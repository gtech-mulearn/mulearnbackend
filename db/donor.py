from django.db import models
from db.user import User
from django.conf import settings


class Donor(models.Model):
    """
    Donor model - stores personal information about donors.
    Payment tracking is handled by the separate Donation model.
    """
    id = models.CharField(primary_key=True, max_length=36)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=200)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount = models.FloatField()
    currency = models.CharField(max_length=30)
    company = models.CharField(max_length=100, null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    pan_number = models.CharField(max_length=10, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    is_organisation = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='donor_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'donor'

