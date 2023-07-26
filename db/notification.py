from django.db import models
from db.user import User


class Notification(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=50)
    description = models.CharField(max_length=200)
    button = models.CharField(max_length=10)
    url = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, db_column='created_by', related_name='created_notifications')

    class Meta:
        managed = False
        db_table = 'notification'
        ordering = ['created_at']