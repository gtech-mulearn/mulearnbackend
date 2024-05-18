from rest_framework import serializers

from db.projects import Project, ProjectImage

class ProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImage
        fields = ['id', 'image_url', 'created_at']

class ProjectSerializer(serializers.ModelSerializer):
    images = ProjectImageSerializer(many=True)
    created_by = serializers.CharField(read_only=True)
    updated_by = serializers.CharField(read_only=True)

    class Meta:
        model = Project
        fields = ['id', 'logo', 'description', 'link', 'contributors', 'created_at', 'updated_at', 'created_by', 'updated_by', 'images']

    def create(self, validated_data):
        images_data = validated_data.pop('images')
        project = Project.objects.create(**validated_data)
        for image_data in images_data:
            ProjectImage.objects.create(project=project, **image_data)
        return project

    def update(self, instance, validated_data):
        images_data = validated_data.pop('images')
        instance.logo = validated_data.get('logo', instance.logo)
        instance.description = validated_data.get('description', instance.description)
        instance.link = validated_data.get('link', instance.link)
        instance.contributors = validated_data.get('contributors', instance.contributors)
        instance.updated_by = validated_data.get('updated_by', instance.updated_by)
        instance.save()

        # Clear existing images and add new ones
        instance.images.all().delete()
        for image_data in images_data:
            ProjectImage.objects.create(project=instance, **image_data)
        return instance
