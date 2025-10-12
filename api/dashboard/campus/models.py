import uuid

from django.db import models

from db.organization import Organization
from db.user import User


class CampusExecom(models.Model):
    """
    Campus Execom Model
    
    This model represents the executive committee members of a campus.
    Each entry links a user to a campus with a specific role.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campus = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='execom_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campus_execom_roles')
    role = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('campus', 'user')
        ordering = ['role', 'created_at']

    def __str__(self):
        return f"{self.user.name} - {self.role} at {self.campus.title}"