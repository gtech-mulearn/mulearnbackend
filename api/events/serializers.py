import uuid
from rest_framework import serializers
from db.events import Event
from db.user import User
from db.task import Category, InterestGroup
from db.organization import Organization


class EventListSerializer(serializers.ModelSerializer):
    """Serializer for listing events with basic details"""
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    scope_org_name = serializers.CharField(source="scope_org.title", read_only=True, allow_null=True)
    scope_ig_name = serializers.CharField(source="scope_ig.title", read_only=True, allow_null=True)
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_image",
            "status",
            "scope",
            "organiser_type",
            "scope_org",
            "scope_org_name",
            "scope_ig",
            "scope_ig_name",
            "start_datetime",
            "end_datetime",
            "venue_type",
            "venue_city",
            "created_by",
            "created_by_name",
            "category",
            "category_name",
            "interest_count",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_by_name",
            "scope_org_name",
            "scope_ig_name",
            "category_name",
            "interest_count",
            "created_at",
        ]


class EventDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed event information"""
    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True)
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)
    updated_by_name = serializers.CharField(source="updated_by.full_name", read_only=True, allow_null=True)
    scope_org_name = serializers.CharField(source="scope_org.title", read_only=True, allow_null=True)
    scope_ig_name = serializers.CharField(source="scope_ig.title", read_only=True, allow_null=True)
    organiser_org_name = serializers.CharField(source="organiser_org.title", read_only=True, allow_null=True)
    organiser_ig_name = serializers.CharField(source="organiser_ig.title", read_only=True, allow_null=True)
    category_name = serializers.CharField(source="category.name", read_only=True, allow_null=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "cover_image",
            "banner_image",
            "status",
            "scope",
            "organiser_type",
            "scope_org",
            "scope_org_name",
            "scope_ig",
            "scope_ig_name",
            "scope_ci_id",
            "organiser_org",
            "organiser_org_name",
            "organiser_ig",
            "organiser_ig_name",
            "organiser_ci_id",
            "start_datetime",
            "end_datetime",
            "registration_url",
            "registration_deadline",
            "min_karma",
            "venue_type",
            "venue_address",
            "venue_city",
            "venue_maps_url",
            "venue_online_link",
            "venue_platform",
            "created_by",
            "created_by_name",
            "created_by_email",
            "updated_by",
            "updated_by_name",
            "category",
            "category_name",
            "is_featured",
            "is_collaboration",
            "interest_count",
            "tags",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "created_by",
            "created_by_name",
            "created_by_email",
            "updated_by_name",
            "scope_org_name",
            "scope_ig_name",
            "organiser_org_name",
            "organiser_ig_name",
            "category_name",
            "interest_count",
            "created_at",
        ]


class EventCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating events"""
    
    class Meta:
        model = Event
        fields = [
            "title",
            "slug",
            "description",
            "cover_image",
            "banner_image",
            "status",
            "scope",
            "scope_org",
            "scope_ig",
            "scope_ci_id",
            "organiser_type",
            "organiser_org",
            "organiser_ig",
            "organiser_ci_id",
            "start_datetime",
            "end_datetime",
            "registration_url",
            "registration_deadline",
            "min_karma",
            "venue_type",
            "venue_address",
            "venue_city",
            "venue_maps_url",
            "venue_online_link",
            "venue_platform",
            "category",
            "is_featured",
            "is_collaboration",
            "tags",
        ]

    def validate_scope(self, value):
        """Validate scope is one of allowed choices"""
        valid_scopes = dict(Event.Scope.choices).keys()
        if value not in valid_scopes:
            raise serializers.ValidationError(f"Invalid scope. Must be one of: {', '.join(valid_scopes)}")
        return value

    def validate_organiser_type(self, value):
        """Validate organiser type is one of allowed choices"""
        valid_types = dict(Event.OrganiserType.choices).keys()
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid organiser type. Must be one of: {', '.join(valid_types)}")
        return value

    def validate_status(self, value):
        """Validate status is one of allowed choices"""
        valid_statuses = dict(Event.Status.choices).keys()
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_venue_type(self, value):
        """Validate venue type is one of allowed choices"""
        valid_types = dict(Event.VenueType.choices).keys()
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid venue type. Must be one of: {', '.join(valid_types)}")
        return value

    def create(self, validated_data):
        """Create a new event"""
        user_id = self.context.get("user_id")
        validated_data["created_by_id"] = user_id
        validated_data["updated_by_id"] = user_id
        
        return Event.objects.create(**validated_data)

    def update(self, instance, validated_data):
        """Update an existing event"""
        user_id = self.context.get("user_id")
        validated_data["updated_by_id"] = user_id
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
