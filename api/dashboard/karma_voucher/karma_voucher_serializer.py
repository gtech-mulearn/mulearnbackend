import uuid

from rest_framework import serializers

from db.user import User
from db.task import VoucherLog
from utils.utils import DateTimeUtils

from utils.permission import JWTUtils

class VoucherLogCSVSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(required=True, allow_null=False)
    task_id = serializers.CharField(required=True, allow_null=False)

    def create(self, validated_data):
        
        current_user = self.context.get('current_user')

        vl = VoucherLog.objects.create(**validated_data, id=uuid.uuid4(), code=uuid.uuid4(), created_by_id=current_user, updated_by_id=current_user, created_at=DateTimeUtils.get_current_utc_time(), updated_at=DateTimeUtils.get_current_utc_time())
        return vl
    
    class Meta:
        model = VoucherLog
        fields = [
            "user_id",
            "task_id",
            "karma",
            "mail",
        ]

class VoucherLogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.fullname')
    task = serializers.CharField(source='task.title')
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')

    class  Meta:
        model = VoucherLog
        fields = '__all__'
