from django.db import models
from user.models import Students


# Create your models here.


class Portal(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    portal_key = models.CharField(max_length=36)
    name = models.CharField(max_length=75)
    link = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'portal'

class PortalUserAuth(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    portal = models.ForeignKey(Portal, models.DO_NOTHING)
    user = models.ForeignKey(Students, models.DO_NOTHING)
    is_authenticated = models.IntegerField()
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'portal_user_auth'

class PortalUserMailValidate(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    portal = models.ForeignKey(Portal, models.DO_NOTHING)
    user = models.ForeignKey(Students, models.DO_NOTHING)
    token = models.CharField(max_length=36)
    expiry = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'portal_user_mail_validate'