from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import json


def validate_projects_json(value):
    """
    Validate that projects field contains a list of valid project objects.
    """
    if not isinstance(value, list):
        raise ValidationError("Projects must be a list.")
    
    for project in value:
        if not isinstance(project, dict):
            raise ValidationError("Each project must be an object.")
        
        # Required fields
        if 'title' not in project or not isinstance(project['title'], str):
            raise ValidationError("Each project must have a 'title' field as string.")
        
        # Optional fields validation
        if 'link' in project and project['link'] and not isinstance(project['link'], str):
            raise ValidationError("Project 'link' must be a string.")
        
        if 'description' in project and project['description'] and not isinstance(project['description'], str):
            raise ValidationError("Project 'description' must be a string.")
        
        if 'tags' in project:
            if not isinstance(project['tags'], list):
                raise ValidationError("Project 'tags' must be a list.")
            for tag in project['tags']:
                if not isinstance(tag, str):
                    raise ValidationError("Each tag must be a string.")


def validate_experience_json(value):
    """
    Validate that experience field contains a list of valid experience objects.
    """
    if not isinstance(value, list):
        raise ValidationError("Experience must be a list.")
    
    for exp in value:
        if not isinstance(exp, dict):
            raise ValidationError("Each experience entry must be an object.")
        
        # Required fields
        required_fields = ['role', 'company']
        for field in required_fields:
            if field not in exp or not isinstance(exp[field], str):
                raise ValidationError(f"Each experience entry must have a '{field}' field as string.")
        
        # Optional date fields validation
        date_fields = ['start', 'end']
        for date_field in date_fields:
            if date_field in exp and exp[date_field]:
                if not isinstance(exp[date_field], str):
                    raise ValidationError(f"Experience '{date_field}' must be a string.")
                # Basic date format validation (YYYY-MM)
                try:
                    date_parts = exp[date_field].split('-')
                    if len(date_parts) != 2:
                        raise ValueError
                    year, month = int(date_parts[0]), int(date_parts[1])
                    if year < 1900 or year > 2100 or month < 1 or month > 12:
                        raise ValueError
                except (ValueError, IndexError):
                    raise ValidationError(f"Experience '{date_field}' must be in YYYY-MM format.")
        
        # Optional description field
        if 'description' in exp and exp['description'] and not isinstance(exp['description'], str):
            raise ValidationError("Experience 'description' must be a string.")


class UserProfile(models.Model):
    """
    Extended user profile model with bio, projects, and experience fields.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Existing fields (assuming these exist in the original model)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, blank=True)
    
    # New fields for enhancement
    bio = models.TextField(
        blank=True,
        null=True,
        help_text="User's biography or personal description"
    )
    
    projects = models.JSONField(
        default=list,
        validators=[validate_projects_json],
        help_text="List of user's projects with title, link, description, and tags"
    )
    
    experience = models.JSONField(
        default=list,
        validators=[validate_experience_json],
        help_text="List of user's work experience with role, company, dates, and description"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_profile'
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def projects_count(self):
        """Return the number of projects."""
        return len(self.projects) if self.projects else 0
    
    def experience_count(self):
        """Return the number of experience entries."""
        return len(self.experience) if self.experience else 0