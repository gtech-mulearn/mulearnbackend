from django.db import models
from user.models import Student


# Create your models here.

class Portal(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    portal_token = models.CharField(max_length=36)
    name = models.CharField(max_length=75)
    link = models.CharField(max_length=100, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portal'


class PortalUserAuth(models.Model):
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE)
    user = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_authenticated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portal_user_auth'


class PortalUserMailValidate(models.Model):
    portal = models.ForeignKey(Portal, on_delete=models.CASCADE)
    user = models.ForeignKey(Student, on_delete=models.CASCADE)
    token = models.CharField(max_length=36, null=False)
    expiry = models.DateTimeField(null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portal_user_mail_validate'
    