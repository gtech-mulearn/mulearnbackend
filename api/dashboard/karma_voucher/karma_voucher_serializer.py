from rest_framework import serializers
from db.task import VoucherLog


class VoucherLogCSVSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(required=True, allow_null=False)
    task_id = serializers.CharField(required=True, allow_null=False)
    created_by_id = serializers.CharField(required=True, allow_null=False)
    updated_by_id = serializers.CharField(required=True, allow_null=False)

    class Meta:
        model = VoucherLog
        fields = ['id', 'code', 'user_id', 'task_id', 'karma', 'mail', 'month', 'week', 'created_by_id', 'updated_by_id', 'created_at', 'updated_at']

class VoucherLogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.fullname')
    task = serializers.CharField(source='task.title')
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')

    class  Meta:
        model = VoucherLog
        fields = '__all__'       