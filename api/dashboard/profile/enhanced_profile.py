# Enhanced Profile Fields Extension for MuLearn Backend
# Add these enhancements to the existing profile system

from django.core.exceptions import ValidationError
from rest_framework import serializers
from db.user import User, UserSettings
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


# Enhanced Profile Serializer Fields
class EnhancedProfileSerializer(serializers.ModelSerializer):
    """
    Add these fields to the existing UserProfileSerializer
    """
    bio = serializers.CharField(
        max_length=1000, 
        required=False, 
        allow_blank=True,
        help_text="User's biography or personal description"
    )
    
    projects = serializers.JSONField(
        default=list,
        required=False,
        help_text="List of user's projects with title, link, description, and tags"
    )
    
    experience = serializers.JSONField(
        default=list,
        required=False,
        help_text="List of user's work experience with role, company, dates, and description"
    )
    
    def validate_projects(self, value):
        """Validate projects JSON structure"""
        validate_projects_json(value)
        return value
    
    def validate_experience(self, value):
        """Validate experience JSON structure"""
        validate_experience_json(value)
        return value


# Enhanced Profile View Methods
class EnhancedProfileViewMixin:
    """
    Add these methods to existing profile views
    """
    
    def update_enhanced_profile(self, user, validated_data):
        """Update user profile with enhanced fields"""
        profile_fields = ['bio', 'projects', 'experience']
        
        # Update or create user settings if needed
        user_settings, created = UserSettings.objects.get_or_create(user=user)
        
        # Update enhanced fields
        for field in profile_fields:
            if field in validated_data:
                setattr(user, field, validated_data[field])
        
        user.save()
        return user
    
    def get_enhanced_profile_data(self, user):
        """Get enhanced profile data"""
        return {
            'bio': getattr(user, 'bio', ''),
            'projects': getattr(user, 'projects', []),
            'experience': getattr(user, 'experience', []),
            'projects_count': len(getattr(user, 'projects', [])),
            'experience_count': len(getattr(user, 'experience', []))
        }