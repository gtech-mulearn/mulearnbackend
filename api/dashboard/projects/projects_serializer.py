import uuid
from rest_framework import serializers
from utils.utils import DateTimeUtils
from db.projects import Projects,ProjectsCommandLink,ProjectsUpvoteLink
from db.user import User

class ProjectsListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = ['id', 'logo', 'description', 'project_image', 'link', 'contributors', 'updated_by', 'updated_at', 'created_by', 'created_at']

    updated_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
    created_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())

class ProjectsCommandLinkListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectsCommandLink
        fields = ['id', 'command', 'project', 'user', 'updated_by', 'updated_at', 'created_by', 'created_at']

    project = serializers.SlugRelatedField(slug_field='id', queryset=Projects.objects.all())
    user = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
    updated_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
    created_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())


class ProjectsUpvoteLinkListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectsUpvoteLink
        fields = ['id', 'vote', 'project', 'user', 'created_at', 'created_by']

    project = serializers.SlugRelatedField(slug_field='id', queryset=Projects.objects.all())
    user = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
    created_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
