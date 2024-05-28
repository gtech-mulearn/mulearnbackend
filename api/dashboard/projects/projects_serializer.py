from rest_framework import serializers

from db.projects import ( 
    Project, 
    ProjectImage,
    Comment, 
    Vote 
)


class VoteSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.full_name')
    updated_by = serializers.CharField(source='updated_by.full_name')
    created_by = serializers.CharField(source='created_by.full_name')
    
    class Meta:
        model = Vote
        fields = "__all__"

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.full_name')
    updated_by = serializers.CharField(source='updated_by.full_name')
    created_by = serializers.CharField(source='created_by.full_name')
    
    class Meta:
        model = Comment
        fields = "__all__"
        
class ProjectImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectImage
        fields = ['image']
            
class ProjectSerializer(serializers.ModelSerializer):
    updated_by = serializers.CharField(source='updated_by.full_name',read_only=True)
    created_by = serializers.CharField(source='created_by.full_name',read_only=True)
    logo = serializers.ImageField(max_length=None, use_url=True)
    images = ProjectImageSerializer(many=True, read_only=True)
    votes = VoteSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    contributors = serializers.CharField(max_length=200, required=False)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "logo",
            "images",
            "description",
            "link",
            "contributors",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "votes",
            "comments"
        ]

class ProjectUpdateSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(max_length=None, use_url=True, required=False)
    contributors = serializers.CharField(required=False)
    title = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    link = serializers.URLField(required=False)

    class Meta:
        model = Project
        fields = [
            "title",
            "logo",
            "images",
            "description",
            "link",
            "contributors"
        ]
        
