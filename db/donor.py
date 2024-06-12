from django.db import models
from db.user import User
from django.conf import settings


class Donor(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    payment_id = models.CharField(max_length=100)
    payment_method = models.CharField(max_length=100)
    amount = models.FloatField()
    currency = models.CharField(max_length=30)
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=200)
    company = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    pan_number = models.CharField(max_length=10)
    created_by = models.ForeignKey(User, on_delete=models.SET(settings.SYSTEM_ADMIN_ID), db_column='created_by', related_name='donor_created_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'donor'
