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
