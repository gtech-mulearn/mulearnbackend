import uuid
from rest_framework import serializers
from db.task import EventConnection, Events
from db.user import User
from utils.utils import DateTimeUtils


class EventConnectionSerializer(serializers.ModelSerializer):
    entity_name = serializers.SerializerMethodField()
    entity_email = serializers.SerializerMethodField()
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.full_name", read_only=True)

    class Meta:
        model = EventConnection
        fields = [
            'id', 'event', 'entity_id', 'entity_type', 'ticket_status',
            'created_at', 'updated_at',
            'entity_name', 'entity_email', 'created_by_name', 'updated_by_name'
        ]

    def get_entity_name(self, obj):
        if obj.entity_type == 'user':
            user = User.objects.filter(id=obj.entity_id).first()
            return user.full_name if user else None
        return None

    def get_entity_email(self, obj):
        if obj.entity_type == 'user':
            user = User.objects.filter(id=obj.entity_id).first()
            return user.email if user else None
        return None


class EventConnectionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventConnection
        fields = ['entity_id', 'entity_type', 'ticket_status']

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        event_id = self.context.get("event_id")
        
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        validated_data["id"] = uuid.uuid4()
        validated_data["event_id"] = event_id
        
        return EventConnection.objects.create(**validated_data)


class EventConnectionStatusSerializer(serializers.ModelSerializer):
    event_name = serializers.CharField(source="event.name", read_only=True)
    event_slug = serializers.CharField(source="event.slug", read_only=True)

    class Meta:
        model = EventConnection
        fields = [
            'id', 'event', 'event_name', 'event_slug', 'ticket_status',
            'created_at', 'updated_at'
        ]


class UserEventSerializer(serializers.ModelSerializer):
    """Serializer for events with user's connection status - basic info only"""
    ticket_status = serializers.SerializerMethodField()
    connection_id = serializers.SerializerMethodField()
    connection_created_at = serializers.SerializerMethodField()
    connection_updated_at = serializers.SerializerMethodField()

    class Meta:
        model = Events
        fields = [
            'id', 'name', 'status', 'event_start_date', 'event_end_date',
            'event_type', 'ticket_status', 'connection_id', 
            'connection_created_at', 'connection_updated_at'
        ]
    
    def get_ticket_status(self, obj):
        if hasattr(obj, 'connection') and obj.connection:
            return obj.connection.ticket_status
        return None
    
    def get_connection_id(self, obj):
        if hasattr(obj, 'connection') and obj.connection:
            return obj.connection.id
        return None
    
    def get_connection_created_at(self, obj):
        if hasattr(obj, 'connection') and obj.connection:
            return obj.connection.created_at
        return None
    
    def get_connection_updated_at(self, obj):
        if hasattr(obj, 'connection') and obj.connection:
            return obj.connection.updated_at
        return None


class EventUserSerializer(serializers.Serializer):
    """Serializer for listing users in an event"""
    user_id = serializers.CharField(source="entity_id")
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    muid = serializers.SerializerMethodField()
    ticket_status = serializers.CharField()
    connection_id = serializers.CharField(source="id")
    connection_created_at = serializers.DateTimeField(source="created_at")
    connection_updated_at = serializers.DateTimeField(source="updated_at")
    
    def get_full_name(self, obj):
        if obj.entity_type == 'user':
            user = User.objects.filter(id=obj.entity_id).first()
            return user.full_name if user else None
        return None
    
    def get_email(self, obj):
        if obj.entity_type == 'user':
            user = User.objects.filter(id=obj.entity_id).first()
            return user.email if user else None
        return None
    
    def get_muid(self, obj):
        if obj.entity_type == 'user':
            user = User.objects.filter(id=obj.entity_id).first()
            return user.muid if user else None
        return None
