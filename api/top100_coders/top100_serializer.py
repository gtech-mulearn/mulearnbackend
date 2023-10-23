from rest_framework import serializers


class Top100CodersSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    first_name = serializers.CharField(source='user__first_name')
    last_name = serializers.CharField(source='user__last_name')
    org_title = serializers.CharField(source='user__user_organization_link_user__org__title')
    district_name = serializers.CharField(source='user__user_organization_link_user__org__district__name')
    state_name = serializers.CharField(source='user__user_organization_link_user__org__district__zone__state__name')
    total_karma = serializers.IntegerField()
