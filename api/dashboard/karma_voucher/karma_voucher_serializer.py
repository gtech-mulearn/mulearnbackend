import uuid
from datetime import datetime
from django.db.models import Q
from rest_framework import serializers
from db.task import VoucherLog, TaskList
from db.user import User
from utils.permission import JWTUtils
from utils.utils import DateTimeUtils
from utils.karma_voucher import generate_ordered_id


ALLOWED_MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

ALLOWED_WEEKS = ['W1', 'W2', 'W3', 'W4', 'W5']


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
        if week and week not in ALLOWED_WEEKS:
            response_data["error"] = f"Week must be one of {ALLOWED_WEEKS}"
            raise serializers.ValidationError(response_data)
        
        month = data.get('month')
        if month and month not in ALLOWED_MONTHS:
             response_data["error"] = f"Month must be one of {ALLOWED_MONTHS}"
             raise serializers.ValidationError(response_data)

        user_id = data.get('user_id')
        task_id = data.get('task_id')
        current_year = DateTimeUtils.get_current_utc_time().year

        if VoucherLog.objects.filter(
            user_id=user_id,
            task_id=task_id,
            month=month,
            week=week,
            created_at__year=current_year
        ).exists():
            response_data["error"] = "Voucher already exists for this user, task, month, and week."
            raise serializers.ValidationError(response_data)

        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        representation['code'] = instance.code
        representation['full_name'] = instance.user.full_name
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
    user = serializers.CharField(source='user.full_name')
    task = serializers.CharField(source='task.title')
    hashtag = serializers.CharField(source='task.hashtag')
    created_by = serializers.CharField(source='created_by.full_name')
    updated_by = serializers.CharField(source='updated_by.full_name')
    muid = serializers.CharField(source="user.muid")

    class Meta:
        model = VoucherLog
        fields = [
            "id",
            "code",
            "user",
            "task",
            "hashtag",
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
        task_ids = list(TaskList.objects.filter(hashtag=value).values_list('id', flat=True)[:2])
        if not task_ids:
            raise serializers.ValidationError("Enter a valid task")
        if len(task_ids) > 1:
            raise serializers.ValidationError(
                "Multiple tasks share this hashtag; contact an admin to resolve the duplicate.")
        return task_ids[0]

    def validate_karma(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a valid karma")
        return value

    def validate_week(self, value):
        if value not in ALLOWED_WEEKS:
            raise serializers.ValidationError(
                f"Week must be one of {ALLOWED_WEEKS}")
        return value
    
    def validate_month(self, value):
        if value not in ALLOWED_MONTHS:
            raise serializers.ValidationError(
                f"Month must be one of {ALLOWED_MONTHS}")
        return value
    
    def validate(self, data):
        user_id = data.get('user')
        task_id = data.get('task')
        month = data.get('month')
        week = data.get('week')
        current_year = DateTimeUtils.get_current_utc_time().year

        if VoucherLog.objects.filter(
            user_id=user_id,
            task_id=task_id,
            month=month,
            week=week,
            created_at__year=current_year
        ).exists():
            raise serializers.ValidationError(
                "Voucher already exists for this user, task, month, and week."
            )
        return data


class VoucherLogUpdateSerializer(serializers.ModelSerializer):
    new_user = serializers.CharField(required=False)
    hashtag = serializers.CharField(required=False)
    new_karma = serializers.IntegerField(required=False)
    new_month = serializers.CharField(required=False)
    new_week = serializers.CharField(required=False)

    class Meta:
        model = VoucherLog
        fields = [
            "new_user",
            "hashtag",
            "new_karma",
            "new_month",
            "new_week",
        ]

    def update(self, instance, validated_data):
        instance.user_id = validated_data.get('new_user', instance.user_id)
        instance.task_id = validated_data.get('hashtag', instance.task_id)
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

    def validate_hashtag(self, value):
        task_ids = list(TaskList.objects.filter(hashtag=value).values_list('id', flat=True)[:2])
        if not task_ids:
            raise serializers.ValidationError("Enter a valid task")
        if len(task_ids) > 1:
            raise serializers.ValidationError(
                "Multiple tasks share this hashtag; contact an admin to resolve the duplicate.")
        return task_ids[0]
    
    def validate_new_karma(self, value):
        if value <= 0:
            raise serializers.ValidationError("Enter a valid karma")
        return value
    
    def validate_new_week(self, value):
        if value not in ALLOWED_WEEKS:
            raise serializers.ValidationError(
                f"Week must be one of {ALLOWED_WEEKS}")
        return value

    def validate_new_month(self, value):
        if value not in ALLOWED_MONTHS:
             raise serializers.ValidationError(
                f"Month must be one of {ALLOWED_MONTHS}")
        return value
    
    def validate(self, data):
        # Use existing instance values if new ones are not provided
        user_id = data.get('new_user', self.instance.user_id)
        task_id = data.get('hashtag', self.instance.task_id)
        month = data.get('new_month', self.instance.month)
        week = data.get('new_week', self.instance.week)
        current_year = DateTimeUtils.get_current_utc_time().year

        if VoucherLog.objects.filter(
            user_id=user_id,
            task_id=task_id,
            month=month,
            week=week,
            created_at__year=current_year
        ).exclude(id=self.instance.id).exists():
             raise serializers.ValidationError(
                "Voucher already exists for this user, task, month, and week."
            )
        return data

    def destroy(self, obj):
        obj.delete()
