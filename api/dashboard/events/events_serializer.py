import uuid
from rest_framework import serializers
from django.utils.text import slugify
from db.task import Events, Category
from utils.utils import DateTimeUtils


class CategorySerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.full_name", read_only=True)
    updated_by = serializers.CharField(source="updated_by.full_name", read_only=True)

    class Meta:
        model = Category
        fields = "__all__"


class EventsListSerializer(serializers.ModelSerializer):
    created_by = serializers.CharField(source="created_by.full_name", read_only=True)
    updated_by = serializers.CharField(source="updated_by.full_name", read_only=True)
    category = serializers.CharField(source="category.name", read_only=True, allow_null=True)
    category_id = serializers.CharField(source="category.id", read_only=True, allow_null=True)

    class Meta:
        model = Events
        fields = "__all__"


class EventsCUDSerializer(serializers.ModelSerializer):
    category = serializers.CharField(required=False, allow_null=True)
    tag = serializers.JSONField(source='tags', required=False, allow_null=True)

    class Meta:
        model = Events
        fields = [
            'name', 'description', 'registration_start_date', 'registration_end_date',
            'event_start_date', 'event_end_date', 'event_start_time', 'event_end_time',
            'user_limit', 'status', 'cover_image', 'event_type', 'location_name',
            'location_address', 'ticket_type', 'ticket_value', 'category', 'tags', 'link', 'tag'
        ]
        extra_kwargs = {
            'ticket_value': {'required': False},
            'link': {'required': False, 'allow_null': True},
            'category': {'required': False, 'allow_null': True},
        }
        read_only_fields = [
            'id', 'slug', 'created_by', 'updated_by', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        
        validated_data["id"] = str(uuid.uuid4())
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        validated_data['slug'] = slugify(validated_data.get('name'))
        
        # Handle category FK
        category_id = validated_data.pop('category', None)
        if category_id:
            try:
                validated_data["category_id"] = category_id
            except:
                pass
        
        # Set default status if not provided
        if 'status' not in validated_data:
            validated_data['status'] = Events.Status.REQUEST.value
        
        return Events.objects.create(**validated_data)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        
        # Handle category FK
        category_id = validated_data.pop('category', None)
        if category_id is not None:
            validated_data["category_id"] = category_id
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if 'name' in validated_data:
            instance.slug = slugify(validated_data['name'])
        
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        
        instance.save()
        return instance
