from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile


class ProjectSerializer(serializers.Serializer):
    """
    Serializer for individual project objects within the projects array.
    """
    title = serializers.CharField(max_length=200, required=True)
    link = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        allow_empty=True
    )


class ExperienceSerializer(serializers.Serializer):
    """
    Serializer for individual experience objects within the experience array.
    """
    role = serializers.CharField(max_length=100, required=True)
    company = serializers.CharField(max_length=100, required=True)
    start = serializers.RegexField(
        regex=r'^\d{4}-\d{2}$',
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={"invalid": "Date must be in YYYY-MM format"}
    )
    end = serializers.RegexField(
        regex=r'^\d{4}-\d{2}$',
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={"invalid": "Date must be in YYYY-MM format"}
    )
    description = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        allow_null=True
    )


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile model with enhanced bio, projects, and experience fields.
    """
    # Read-only fields from User model
    username = serializers.CharField(source='user.username', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    # Profile fields
    full_name = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()
    experience_count = serializers.SerializerMethodField()
    
    # Enhanced fields with validation
    projects = serializers.ListField(
        child=ProjectSerializer(),
        required=False,
        allow_empty=True
    )
    experience = serializers.ListField(
        child=ExperienceSerializer(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'user_id',
            'username',
            'first_name',
            'last_name',
            'full_name',
            'email',
            'phone',
            'bio',
            'projects',
            'projects_count',
            'experience',
            'experience_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'user_id',
            'username',
            'full_name',
            'projects_count',
            'experience_count',
            'created_at',
            'updated_at',
        ]
    
    def get_full_name(self, obj):
        """Return the user's full name."""
        return obj.get_full_name()
    
    def get_projects_count(self, obj):
        """Return the number of projects."""
        return obj.projects_count()
    
    def get_experience_count(self, obj):
        """Return the number of experience entries."""
        return obj.experience_count()
    
    def validate_projects(self, value):
        """
        Validate projects field structure.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Projects must be a list.")
        
        # Validate each project using ProjectSerializer
        for i, project in enumerate(value):
            project_serializer = ProjectSerializer(data=project)
            if not project_serializer.is_valid():
                raise serializers.ValidationError(
                    f"Project {i + 1}: {project_serializer.errors}"
                )
        
        return value
    
    def validate_experience(self, value):
        """
        Validate experience field structure.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Experience must be a list.")
        
        # Validate each experience using ExperienceSerializer
        for i, exp in enumerate(value):
            exp_serializer = ExperienceSerializer(data=exp)
            if not exp_serializer.is_valid():
                raise serializers.ValidationError(
                    f"Experience {i + 1}: {exp_serializer.errors}"
                )
        
        return value
    
    def update(self, instance, validated_data):
        """
        Update user profile with partial data support.
        Only update fields that are provided in the request.
        """
        # Update only the fields that are provided
        for field_name, value in validated_data.items():
            if hasattr(instance, field_name):
                setattr(instance, field_name, value)
        
        instance.save()
        return instance


class UserProfileCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating user profiles.
    """
    class Meta:
        model = UserProfile
        fields = [
            'first_name',
            'last_name',
            'email',
            'phone',
            'bio',
            'projects',
            'experience',
        ]
        
    def create(self, validated_data):
        """
        Create a new user profile.
        """
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)