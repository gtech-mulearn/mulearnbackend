from django.db import models
import uuid
from db.user import User

class Achievement(models.Model):
    id                = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    name              = models.CharField(max_length=75, unique=True)
    level_based       = models.BooleanField()
    description       = models.CharField(max_length=300)
    icon              = models.CharField(max_length=100)
    has_vc            = models.BooleanField()
    tags              = models.JSONField()
    type              = models.CharField(max_length=36)
    template_id       = models.CharField(max_length=100, null=True, blank=True)
    updated_by        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_updated', db_column='updated_by')
    updated_at        = models.DateTimeField(auto_now=True)
    created_by        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_created', db_column='created_by')
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'achievement'
        managed = False


class UserAchievements(models.Model):
    id                 = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user_id            = models.ForeignKey('User', on_delete=models.CASCADE, related_name='achievements', db_column='user_id', db_index=True)
    achievement_id     = models.ForeignKey('Achievement', on_delete=models.CASCADE, related_name='users', db_column='achievement_id', db_index=True)
    is_issued          = models.BooleanField(default=False)
    vc_url             = models.CharField(max_length=100)
    # updated_by         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_updated',db_column='updated_by')
    # updated_at         = models.DateTimeField(auto_now=True)
    # created_by         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements_created',db_column='created_by')
    # created_at         = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_achievements'
        managed = False
