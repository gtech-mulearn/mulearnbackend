from django.db import models
from db.user import User

class KKEMAuthorization(models.Model):
    id = models.CharField(max_length=36, primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='kkem_authorizations')
    dwms_id = models.CharField(max_length=36, unique=True)
    verified = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kkem_authorization'

    def __str__(self):
        return self.id