from rest_framework import serializers
from db.skill import Skill, TaskSkillLink


class SkillSerializer(serializers.ModelSerializer):
    """Full skill serializer for CRUD operations"""
    
    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'code', 'description', 'icon', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class SkillDropdownSerializer(serializers.ModelSerializer):
    """Minimal serializer for dropdown selections"""
    
    class Meta:
        model = Skill
        fields = ['id', 'name', 'code']


class SkillCreateSerializer(serializers.Serializer):
    """Serializer for skill creation"""
    name = serializers.CharField(max_length=75)
    code = serializers.CharField(max_length=20)
    description = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True)
    is_active = serializers.BooleanField(default=True)


class SkillUpdateSerializer(serializers.Serializer):
    """Serializer for skill update"""
    name = serializers.CharField(max_length=75, required=False)
    code = serializers.CharField(max_length=20, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    icon = serializers.CharField(max_length=100, required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


class TaskSkillLinkSerializer(serializers.ModelSerializer):
    """Serializer for task-skill links"""
    skill = SkillDropdownSerializer(read_only=True)
    
    class Meta:
        model = TaskSkillLink
        fields = ['id', 'skill', 'created_at']
