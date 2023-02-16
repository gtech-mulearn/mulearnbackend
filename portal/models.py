from django.db import models
from user.models import User


# Create your models here.

class Portal(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    access_id = models.CharField(max_length=36)
    title = models.CharField(max_length=100)
    link = models.CharField(max_length=100, null=True)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portal'


class PortalUserAuth(models.Model):
    portal_id = models.ForeignKey(Portal, db_constraint="fk_portal_user_auth_ref_portal_id", on_delete=models.CASCADE)
    user_id = models.ForeignKey(User, db_constraint="fk_portal_user_auth_ref_user_id", on_delete=models.CASCADE)
    is_authenticated = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'portal_user_auth'
