from rest_framework import serializers
from db.intern import UserInternGuildLink
from utils.types import InternGuildStatus

class ManageInternSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    mu_id = serializers.CharField(write_only=True, required=False)
    user_id = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = UserInternGuildLink
        fields = ['id', 'user', 'full_name', 'muid', 'mu_id', 'user_id', 'guild', 'status', 'created_at']
        read_only_fields = ['user']

    def validate(self, attrs):
        from db.user import User
        
        user_id = attrs.pop('user_id', None)
        mu_id = attrs.pop('mu_id', None)
        
        # If we are creating (not updating) or if we explicitly want to change the user
        if not self.instance:
            if not user_id and not mu_id:
                raise serializers.ValidationError({"user": "Either user_id or mu_id is required."})
            
            user = None
            if mu_id:
                user = User.objects.filter(muid=mu_id).first()
                if not user:
                    raise serializers.ValidationError({"mu_id": "User with this mu_id not found."})
            elif user_id:
                user = User.objects.filter(id=user_id).first()
                if not user:
                    raise serializers.ValidationError({"user_id": "User with this user_id not found."})
            
            if user:
                # Check if user is already an intern
                if UserInternGuildLink.objects.filter(user=user).exists():
                    raise serializers.ValidationError({"user": "This user is already onboarded as an intern."})
                attrs['user'] = user
                
        return attrs

    def create(self, validated_data):
        from django.db import transaction
        from db.user import UserRoleLink, Role
        from utils.types import RoleType
        
        user_id = self.context.get('user_id')
        validated_data['created_by_id'] = user_id
        validated_data['updated_by_id'] = user_id
        if 'status' not in validated_data:
            validated_data['status'] = InternGuildStatus.ACTIVE.value
            
        with transaction.atomic():
            guild_link = super().create(validated_data)
            
            # Auto-assign "Intern" role
            intern_user = guild_link.user
            intern_role = Role.objects.get(title=RoleType.INTERN.value)
            
            UserRoleLink.objects.get_or_create(
                user=intern_user,
                role=intern_role,
                defaults={
                    'verified': True,
                    'is_active': True,
                    'created_by_id': user_id
                }
            )
            
            return guild_link

    def update(self, instance, validated_data):
        from django.db import transaction
        from db.user import UserRoleLink, Role
        from utils.types import RoleType
        
        user_id = self.context.get('user_id')
        validated_data['updated_by_id'] = user_id
        
        old_status = instance.status
        new_status = validated_data.get('status', old_status)
        
        if old_status == InternGuildStatus.ON_LEAVE.value and new_status != InternGuildStatus.ON_LEAVE.value:
            validated_data['previous_status'] = None
        
        with transaction.atomic():
            guild_link = super().update(instance, validated_data)
            
            # Sync user role based on status
            if new_status == InternGuildStatus.INACTIVE.value:
                UserRoleLink.objects.filter(user=guild_link.user, role__title=RoleType.INTERN.value).delete()
            else:
                intern_role = Role.objects.get(title=RoleType.INTERN.value)
                UserRoleLink.objects.get_or_create(
                    user=guild_link.user,
                    role=intern_role,
                    defaults={
                        'verified': True,
                        'is_active': True,
                        'created_by_id': user_id
                    }
                )
            
            return guild_link
