import uuid
from rest_framework import serializers
from utils.utils import DateTimeUtils
from django.utils import timezone
from db.projects import Project, ProjectCommandLink, ProjectVote
from db.user import User

# Project Serializers

class ProjectRetrieveSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    updated_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)

    class Meta:
        model = Project
        fields = '__all__'

class ProjectCUDSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField()
    project_image = serializers.ImageField()

    class Meta:
        model = Project
        fields = ['logo', 'description', 'project_image', 'link', 'contributors']

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        validated_data['created_by'] = User.objects.get(id=user_id)
        validated_data['updated_by'] = User.objects.get(id=user_id)
        validated_data['created_at'] = timezone.now()
        validated_data['updated_at'] = timezone.now()
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        validated_data['updated_by'] = User.objects.get(id=user_id)
        return super().update(instance, validated_data)

# ProjectCommandLink Serializers

class ProjectCommandLinkRetrieveSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    updated_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)

    class Meta:
        model = ProjectCommandLink
        fields = '__all__'

class ProjectCommandLinkCUDSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
    updated_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())

    class Meta:
        model = ProjectCommandLink
        fields = ['id', 'command', 'project_id', 'user_id', 'created_at', 'created_by', 'updated_at', 'updated_by']

# ProjectVote Serializers

class ProjectVoteRetrieveSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    user_id = serializers.SlugRelatedField(slug_field='full_name', read_only=True)

    class Meta:
        model = ProjectVote
        fields = '__all__'

class ProjectVoteCreateUpdateDeleteSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
    user_id = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())

    class Meta:
        model = ProjectVote
        fields = ['id', 'vote', 'project_id', 'user_id', 'created_at', 'created_by']
