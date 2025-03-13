from django.db import models
from db.user import User
import uuid

class Achievement(models.Model):
    id                = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    title             = models.CharField(max_length=75, unique=True)
    level_based       = models.BooleanField()
    description       = models.CharField(max_length=300)
    icon              = models.CharField(max_length=100)
    has_vc            = models.BooleanField()
    tags              = models.JSONField()
    type              = models.CharField(max_length=36)
    updated_by        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_updated', db_column='updated_by')
    updated_at        = models.DateTimeField(auto_now=True)
    created_by        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_created', db_column='created_by')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'achievement'
        managed = False