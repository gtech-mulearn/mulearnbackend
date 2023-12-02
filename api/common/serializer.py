from rest_framework import serializers


class StudentInfoSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    muid = serializers.CharField()
    circle_name = serializers.CharField()
    circle_ig = serializers.CharField()
    organisation = serializers.CharField()
    dwms_id = serializers.CharField(allow_null=True)
    karma_earned = serializers.IntegerField()


class CollegeInfoSerializer(serializers.Serializer):
    org_title = serializers.CharField()
    learning_circle_count = serializers.CharField()
    user_count = serializers.CharField()


class LearningCircleEnrollmentSerializer(serializers.Serializer):
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    muid = serializers.CharField()
    email = serializers.CharField()
    dwms_id = serializers.CharField(allow_null=True)
    circle_name = serializers.CharField()
    circle_ig = serializers.CharField()
    organisation = serializers.CharField()
    district = serializers.CharField(allow_null=True)
    karma_earned = serializers.IntegerField()
