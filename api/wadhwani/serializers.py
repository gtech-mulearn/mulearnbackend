from rest_framework import serializers


class WadhwaniCollegeLeaderboardSerializer(serializers.Serializer):
    code = serializers.CharField()
    title = serializers.CharField()
    total_karma = serializers.IntegerField()
    students = serializers.IntegerField()

class WadhwaniZoneLeaderboardSerializer(serializers.Serializer):
    zone_name = serializers.CharField()
    total_karma = serializers.IntegerField()
    students = serializers.IntegerField()