from django.db import models

from db.organization import Organization


class LaunchPadUsers(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    email = models.CharField(max_length=255, unique=True)
    phone_number = models.CharField(max_length=15, null=True)
    full_name = models.CharField(max_length=255, null=True)
    district = models.CharField(max_length=100, null=True)
    zone = models.CharField(max_length=100, null=True)
    role = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class LaunchPadUserCollegeLink(models.Model):
    id = models.CharField(primary_key=True, max_length=36)
    user = models.ForeignKey(LaunchPadUsers, on_delete=models.CASCADE)
    college = models.ForeignKey(Organization, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(LaunchPadUsers, on_delete=models.CASCADE, related_name='launchpad_user_college_link_created_by')
    updated_by = models.ForeignKey(LaunchPadUsers, on_delete=models.CASCADE, related_name='launchpad_user_college_link_updated_by')

