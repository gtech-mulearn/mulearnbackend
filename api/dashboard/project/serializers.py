import uuid
from rest_framework import serializers
from utils.utils import DateTimeUtils
from django.utils import timezone
from db.projects import Project, ProjectCommandLink, ProjectVote,ProjectImage
from db.user import User

class MemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'muid', 'full_name']
        
class ProjectImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField()
    
    class Meta:
        model = ProjectImage
        fields = ['image','created_at']
        read_only_fields = ['created_at'] 

class ProjectRetrieveSerializer(serializers.ModelSerializer):
    created_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    updated_by = serializers.SlugRelatedField(slug_field='full_name', read_only=True)
    members = MemberSerializer(many=True, read_only=True)
    images = ProjectImageSerializer(many=True,read_only=True)
    
    class Meta:
        model = Project
        fields = '__all__'

class ProjectCUDSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField()
    members = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=User.objects.all()),
        write_only=True
    )
    images = serializers.ListField(
        child=serializers.ImageField(),write_only=True
    )
    
    class Meta:
        model = Project
        fields = ['logo', 'description', 'link', 'members','images']

    def create(self, validated_data):
        user_id = self.context.get('user_id')
        members_data = validated_data.pop('members', None)
        project_image_list = validated_data.pop('images', None)
        project = Project.objects.create(
            created_by=User.objects.get(id=user_id),
            updated_by=User.objects.get(id=user_id),
            **validated_data
        )
        if members_data:
            project.members.set(members_data) 
        if project_image_list:
            for project_image in project_image_list:
                ProjectImage.objects.create(project=project, image=project_image)
        return project

    def update(self, instance, validated_data):
        user_id = self.context.get('user_id')
        members_data = validated_data.pop('members', None)
        project_image_list = validated_data.pop('images', None)
        
        instance.updated_by = User.objects.get(id=user_id)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if members_data:
            instance.members.set(members_data)
        
        if project_image_list:
            instance.images.all().delete()  # Delete existing images
            for project_image in project_image_list:
                ProjectImage.objects.create(project=instance, image=project_image)
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
