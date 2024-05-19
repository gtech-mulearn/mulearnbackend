import uuid
from rest_framework import serializers
from db.projects import Command, Projects, ProjectImages, ProjectContributors, Vote
from db.user import User
from utils.utils import DateTimeUtils


class ProjectImagesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImages
        fields = ['image']


class ProjectContributorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectContributors
        fields = ['name']


class ProjectsSerializer(serializers.ModelSerializer):
    project_image = ProjectImagesSerializer()
    contributors = ProjectContributorsSerializer()
    created_by = serializers.CharField(source="created_by.full_name")
    updated_by = serializers.CharField(source="updated_by.full_name")

    class Meta:
        model = Projects
        fields = "__all__"


class ProjectsCUDSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projects
        fields = ['name']

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        projectContributors = validated_data.pop("contributors", None)
        projectImages = validated_data.pop("project_image", None)
        validated_data["id"] = uuid.uuid4()
        if projectContributors:
            for contributor in projectContributors:
                ProjectContributors.objects.create(name=contributor)
        if projectImages:
            for project_image in projectImages:
                ProjectImages.objects.create(image=project_image)
        return Projects.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")

        instance.title = validated_data.get("name", instance.name)
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        projectContributors = validated_data.pop("contributors", None)
        projectImages = validated_data.pop("project_image", None)
        instance.save()
        if projectContributors:
            for contributor in projectContributors:
                ProjectContributors.objects.create(name=contributor)
        if projectImages:
            for project_image in projectImages:
                ProjectImages.objects.create(image=project_image)
        instance.save()
        return instance


class ProjectsVoteSerializer(serializers.ModelSerializer):
    project_id = serializers.SlugRelatedField(
        slug_field='id', queryset=Projects.objects.all())

    class Meta:
        model = Vote
        fields = ['vote', 'project_id']

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        return Vote.objects.create(**validated_data)


class ProjectsCommandSerializer(serializers.ModelSerializer):
    project_id = serializers.SlugRelatedField(
        slug_field='id', queryset=Projects.objects.all())

    class Meta:
        model = Command
        fields = ['vote', 'project_id']

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        return Command.objects.create(**validated_data)
