import uuid

from django.db import models

from db.user import User


class Integration(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False)
    token = models.CharField(max_length=400, null=False)
    created_at = models.DateTimeField(null=False)
    updated_at = models.DateTimeField(null=False)

    class Meta:
        db_table = 'integration'


#
class IntegrationAuthorization(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.OneToOneField(Integration, on_delete=models.CASCADE, null=False, related_name="integration_authorization_integration", unique=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='integration_authorization_user', null=False, unique=True)
    integration_value = models.CharField(max_length=255, unique=True, null=False)
    verified = models.BooleanField(default=False, null=False)
    updated_at = models.DateTimeField(null=False)
    created_at = models.DateTimeField(null=False)

    class Meta:
        db_table = 'integration_authorization'
