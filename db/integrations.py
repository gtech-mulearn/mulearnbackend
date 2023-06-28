from datetime import timezone
from django.db import models
from db.user import User
import uuid

from utils.utils import CommonUtils
# from background_task import background

class Integration(models.Model):
    id = models.CharField(max_length=255, primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'integration'

class IntegrationAuthorization(models.Model):
    id = models.CharField(max_length=255, primary_key=True, default=uuid.uuid4, editable=False)
    integration = models.OneToOneField(Integration, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='integration_authorization_user')
    integration_value = models.CharField(max_length=36, unique=True)
    verified = models.BooleanField(default=False)
    updated_at = models.DateTimeField()
    created_at = models.DateTimeField()
    
    class Meta:
        db_table = 'integration_authorization'
        
    # def is_expired(self):
    #     expiration_time = self.created_at + timezone.timedelta(minutes=15)
    #     return timezone.now() > expiration_time and not self.verified

# @background(schedule=timezone.timedelta(minutes=30))
# def delete_expired_verification_links():
#     expired_links = IntegrationAuthorization.objects.filter(is_expired=True)
#     expired_links.delete()

