from django.db import models
import uuid
from db.user import User

class Achievement(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    title = models.CharField(max_length=75, unique=True)
    level_based = models.BooleanField(default=False)
    description = models.CharField(max_length=300)
    icon = models.CharField(max_length=100)
    has_vc = models.BooleanField(default=False)
    tags = models.JSONField()
    type = models.CharField(max_length=36)

    updated_by = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='achievements_updated_by'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='achievements_created_by'
    )

    class Meta:
        db_table = 'achievement'
        managed = False

class UserAchievements(models.Model):
    id = models.CharField(primary_key=True, default=uuid.uuid4, max_length=36)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, 
        related_name='user_achievements'
    )
    achievement = models.ForeignKey(
        Achievement, on_delete=models.CASCADE, 
        related_name='achieved_by_users'
    )
    is_issued = models.BooleanField(default=False)
    vc_url = models.CharField(max_length=100, blank=True, null=True)

    # updated_by = models.ForeignKey(
    #     User, on_delete=models.CASCADE, 
    #     related_name='user_achievements_updated_by'
    # )
    # updated_at = models.DateTimeField(auto_now=True)
    # created_by = models.ForeignKey(
    #     User, on_delete=models.CASCADE, 
    #     related_name='user_achievements_created_by'
    # )
    # created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_achievements'
        managed = False
