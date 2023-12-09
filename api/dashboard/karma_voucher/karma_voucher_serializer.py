import uuid
from django.db.models import Q
from rest_framework import serializers
from db.task import VoucherLog, TaskList
from db.user import User
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils
from utils.karma_voucher import generate_ordered_id

class VoucherLogCSVSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(required=True, allow_null=False)
    task_id = serializers.CharField(required=True, allow_null=False)
    created_by_id = serializers.CharField(required=True, allow_null=False)
    updated_by_id = serializers.CharField(required=True, allow_null=False)
    week = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = VoucherLog
        fields = [
            'id', 
            'code', 
            'user_id', 
            'task_id', 
            'karma', 
            'month', 
            'week', 
            'claimed', 
            'created_by_id',
            'updated_by_id', 
            'created_at', 
            'updated_at', 
            'event', 
            'description'
            ]   

    def validate(self, data):
        response_data = {}
        response_data["code"] = data.get('code')
        week = data.get('week')
        if week and len(str(week)) > 2:
            response_data["error"] = "Week must not exceed 2 characters in length and should be of the format 'W1'"
            raise serializers.ValidationError(response_data)
        return data
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['code'] = instance.code
        representation['fullname'] = instance.user.fullname
        representation['email'] = instance.user.email
        representation['muid'] = instance.user.muid 
        representation['hashtag'] = instance.task.hashtag
        representation['month'] = instance.month
        representation['karma'] = instance.karma
        representation['week'] = instance.week if instance.week else None
        representation['description'] = instance.description if instance.description else None
        representation['event'] = instance.event if instance.event else None

        return representation

class VoucherLogSerializer(serializers.ModelSerializer):
    user = serializers.CharField(source='user.fullname')
    task = serializers.CharField(source='task.title')
    created_by = serializers.CharField(source='created_by.fullname')
    updated_by = serializers.CharField(source='updated_by.fullname')
    muid = serializers.CharField(source="user.muid")

    class Meta:
        model = VoucherLog
        fields = [
            "id",
            "code",
            "user",
            "task",
            "karma",
            "month",
            "week",
            "claimed",
            "description",
            "event",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
            "muid"
        ]

class VoucherLogCreateSerializer(serializers.ModelSerializer):
    user = serializers.CharField(required=True, error_messages={
        'required': 'user field must not be left blank.'
        })
    task = serializers.CharField(required=True, error_messages={
        'required': 'task field must not be left blank.'
        })
    karma = serializers.IntegerField(required=True, error_messages={
        'required': 'karma field must not be left blank.'
        })
    month = serializers.CharField(required=True, error_messages={
        'required': 'month field must not be left blank.'
        })
    week = serializers.CharField(required=True, error_messages={
        'required': 'week field must not be left blank.'
        })

    class Meta:
        model = VoucherLog
        fields = [
            "user",
            "task",
            "karma",
            "month",
            "week",
        ]

    def create(self, validated_data):
        user_id = JWTUtils.fetch_user_id(self.context.get('request'))
        validated_data['user_id'] = validated_data.pop('user')
        validated_data['task_id'] = validated_data.pop('task')
        validated_data['id'] = uuid.uuid4()
        
        existing_codes = set(VoucherLog.objects.values_list('code', flat=True))
        count = 1
        while generate_ordered_id(count) in existing_codes:
            count += 1

        validated_data['code'] = generate_ordered_id(count)
        validated_data['claimed'] = False
        validated_data['updated_by_id'] = user_id
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['created_by_id'] = user_id
        validated_data['created_at'] = DateTimeUtils.get_current_utc_time()
        return VoucherLog.objects.create(**validated_data)

    def validate_user(self, value):
        user = User.objects.filter(Q(muid=value) | Q(email=value)).first()
        if not user:
            raise serializers.ValidationError("Enter a valid user")
        return user.id
    
    def validate_task(self, value):
        if not TaskList.objects.filter(id=value).exists():
            raise serializers.ValidationError("Enter a valid task")
        return value
    
    def validate_karma(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a valid karma")
        return value
    
    def validate_week(self, value):
        if len(value) != 2:
            raise serializers.ValidationError("Week must have exactly two characters.")
        return value
    
class VoucherLogUpdateSerializer(serializers.ModelSerializer):
    new_user = serializers.CharField(required=False)
    new_task = serializers.CharField(required=False)
    new_karma = serializers.IntegerField(required=False)
    new_month = serializers.CharField(required=False)
    new_week = serializers.CharField(required=False)

    class Meta:
        model = VoucherLog
        fields = [
            "new_user",
            "new_task",
            "new_karma",
            "new_month",
            "new_week",
        ]

    def update(self, instance, validated_data):
        instance.user_id = validated_data.get('new_user', instance.user)
        instance.task_id = validated_data.get('new_task', instance.task)
        instance.karma = validated_data.get('new_karma', instance.karma)
        instance.month = validated_data.get('new_month', instance.month)
        instance.week = validated_data.get('new_week', instance.week)
        
        instance.updated_by_id = self.context.get('user_id')
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance 

    def validate_new_user(self, value):
        user = User.objects.filter(Q(muid=value) | Q(email=value)).first()
        if not user:
            raise serializers.ValidationError("Enter a valid user")
        return user.id
    
    def destroy(self, obj):
        obj.delete()