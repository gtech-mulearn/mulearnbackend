from django.db import models
from user.models import User

# Create your models here.

class Portal(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    access_id = models.CharField(max_length=36)
    title = models.CharField(max_length=100)
    link = models.CharField(max_length=100)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'portal'


class PortalUser(models.Model):
    portal_id = models.ForeignKey(Portal, on_delete=models.CASCADE) 
    user_id = models.ForeignKey(User, on_delete=models.CASCADE)  
    is_authenticated = models.BooleanField(default=False)
    created_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username

    class Meta:
        db_table = 'portal-user-link'    