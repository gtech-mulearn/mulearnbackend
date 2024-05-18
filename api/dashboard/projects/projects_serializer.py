from rest_framework import serializers
from db.projects import Project, ProjectContributorsLink, ProjectImages
from api.dashboard.user.dash_user_serializer import UserDashboardSerializer
from django.db.transaction import atomic
from db.user import User


class ContributorSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField("get_user")
    class Meta:
        model = ProjectContributorsLink
        fields = ["id", "user"]
    
    def get_user(self, instance):
        return {
            "id": instance.user.id,
            "full_name": instance.user.full_name,
            "muid": instance.user.muid
        }

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "full_name", "muid"]

class ProjectListSerializer(serializers.ModelSerializer):
    project_contributor = ContributorSerializer(many=True)
    created_by = serializers.SerializerMethodField("get_user")
    updated_by = serializers.SerializerMethodField("get_user")
    upvote = serializers.SerializerMethodField("get_upvote_count")
    class Meta:
        model = Project
        fields = ['id', 'logo', 'description', 'project_image', 'link', 'created_by', 'created_at', 'updated_at', 'updated_by', 'project_contributor', 'upvote']

    def get_user(self, instance):
        return {
            "id": instance.created_by.id,
            "full_name": instance.created_by.full_name,
            "muid": instance.created_by.muid
        }

    def get_upvote_count(self, instace):
        return instace.project_upvote.count()


class ProjectSerializer(serializers.ModelSerializer):
    images = serializers.ListField(child=serializers.URLField(), allow_empty=True)
    class Meta:
        model = Project
        fields = ['logo', 'description', 'images', 'link']

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        members = self.context.get("members")
        validated_data['created_by_id'] = user_id
        with atomic():
            images = validated_data.pop("images")
            project = Project.objects.create(**validated_data)
            ProjectContributorsLink.objects.create(user_id=user_id, project=project)
            for image in images:
                ProjectImages.objects.create(project=project, image=image)
            if members:
                for member in members:
                    if member == user_id: continue
                    ProjectContributorsLink.objects.create(user_id=member, project=project)
            return project
    
    def update(self, instance, validated_data):
        instance.logo = validated_data['logo']
        instance.description = validated_data['description']
        instance.link = validated_data['link']
        user_id = self.context.get("user_id")
        instance.updated_by_id = user_id
        images = validated_data['images']
        with atomic():
            instance.project_image.all().delete()
            for image in images:
                ProjectImages.objects.create(project=instance, image=image)
            instance.project_contributor.all().delete()
            members = self.context.get("members")
            ProjectContributorsLink.objects.create(user_id=user_id, project=instance)
            if members:
                for member in members:
                    if member == user_id:
                        continue
                    ProjectContributorsLink.objects.create(user_id=member, project=instance)
            instance.save()
            return instance

        

    