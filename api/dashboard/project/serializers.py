import uuid
from rest_framework import serializers
from utils.utils import DateTimeUtils
from django.utils import timezone
from db.projects import Project, ProjectCommandLink, ProjectVote
from db.user import User

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'muid', 'full_name']

class ProjectRetrieveSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    updated_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    members = MemberSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = '__all__'

class ProjectCUDSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField()
    project_image = serializers.ImageField()
    members = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=User.objects.all()),
        write_only=True
    )

    class Meta:
        model = Project
        fields = ['logo', 'description', 'project_image', 'link', 'members']

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        members_data = validated_data.pop('members')
        project = Project.objects.create(
            created_by=User.objects.get(id=user_id),
            updated_by=User.objects.get(id=user_id),
            created_at=timezone.now(),
            updated_at=timezone.now(),
            **validated_data
        )
        project.members.set(members_data)
        return project

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        members_data = validated_data.pop('members', None) 
        
        instance.updated_by = User.objects.get(id=user_id)
        instance.updated_at = timezone.now()

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if members_data:
            instance.members.set(members_data)

        return instance



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


class ProjectVoteRetrieveSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    user_id = serializers.SlugRelatedField(slug_field='full_name', read_only=True)

    class Meta:
        model = ProjectVote
        fields = '__all__'

class ProjectVoteCUDSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())
    user_id = serializers.SlugRelatedField(slug_field='id', queryset=User.objects.all())

    class Meta:
        model = ProjectVote
        fields = ['id', 'vote', 'project_id', 'user_id', 'created_at', 'created_by']
