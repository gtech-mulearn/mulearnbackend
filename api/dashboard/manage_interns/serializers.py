from rest_framework import serializers
from django.db import transaction

from db.intern import UserInternGuildLink
from db.user import User, UserRoleLink, Role
from utils.types import InternGuildStatus, RoleType


class ManageInternSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name', read_only=True)
    muid = serializers.CharField(source='user.muid', read_only=True)
    mu_id = serializers.CharField(write_only=True, required=False)
    user_id = serializers.CharField(write_only=True, required=False)
    role = serializers.CharField(required=False)

    class Meta:
        model = UserInternGuildLink
        fields = ['id', 'user', 'full_name', 'muid', 'mu_id', 'user_id', 'guild', 'status', 'role', 'roles', 'created_at']
        read_only_fields = ['user']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Collect all intern-type roles the user currently holds
        intern_role_titles = [RoleType.INTERN.value, RoleType.INTERN_LEAD.value]
        
        # Check if we have prefetched data to avoid N+1 queries
        if hasattr(instance.user, '_prefetched_objects_cache') and 'user_role_link_user' in instance.user._prefetched_objects_cache:
            active_roles = [
                link.role.title for link in instance.user.user_role_link_user.all()
                if link.role.title in intern_role_titles
            ]
        else:
            active_roles = list(
                UserRoleLink.objects.filter(
                    user=instance.user,
                    role__title__in=intern_role_titles
                ).values_list('role__title', flat=True)
            )
            
        data['roles'] = active_roles
        # Legacy 'role' field: prefer Intern Lead if held, else Intern
        data['role'] = (
            RoleType.INTERN_LEAD.value if RoleType.INTERN_LEAD.value in active_roles
            else RoleType.INTERN.value
        )
        return data

    def validate_role(self, value):
        allowed = [RoleType.INTERN.value, RoleType.INTERN_LEAD.value]
        if value not in allowed:
            raise serializers.ValidationError(
                f"Invalid role. Allowed values: {allowed}"
            )
        return value

    def validate(self, attrs):
        user_id = attrs.pop('user_id', None)
        mu_id = attrs.pop('mu_id', None)

        # Only required on create
        if not self.instance:
            if not user_id and not mu_id:
                raise serializers.ValidationError({"user": "Either user_id or mu_id is required."})

            user = None
            if mu_id:
                user = User.objects.filter(muid=mu_id).first()
                if not user:
                    raise serializers.ValidationError({"mu_id": "No user found with this mu_id."})
            elif user_id:
                user = User.objects.filter(id=user_id).first()
                if not user:
                    raise serializers.ValidationError({"user_id": "No user found with this user_id."})

            if UserInternGuildLink.objects.filter(user=user).exists():
                raise serializers.ValidationError({"user": "This user is already onboarded as an intern."})

            attrs['user'] = user

        return attrs

    def _get_role_obj(self, role_title):
        """Fetch a Role by title, raising a clean error if it's missing from the DB."""
        role = Role.objects.filter(title=role_title).first()
        if not role:
            raise serializers.ValidationError(
                {"role": f"Role '{role_title}' does not exist in the system."}
            )
        return role

    def _assign_role(self, user, role_title, actor_user_id):
        """Additively assign the given intern-type role.

        A user can hold both 'Intern' and 'Intern Lead' simultaneously.
        Assigning 'Intern Lead' also ensures 'Intern' is present.
        Assigning 'Intern' alone does NOT strip 'Intern Lead' if already held.
        """
        roles_to_assign = [role_title]
        # Intern Lead implies Intern — keep both
        if role_title == RoleType.INTERN_LEAD.value:
            roles_to_assign.append(RoleType.INTERN.value)

        for title in roles_to_assign:
            role = self._get_role_obj(title)
            UserRoleLink.objects.get_or_create(
                user=user,
                role=role,
                defaults={'verified': True, 'is_active': True, 'created_by_id': actor_user_id}
            )

    def create(self, validated_data):
        actor_user_id = self.context.get('user_id')
        role_title = validated_data.pop('role', RoleType.INTERN.value)

        validated_data['created_by_id'] = actor_user_id
        validated_data['updated_by_id'] = actor_user_id
        validated_data.setdefault('status', InternGuildStatus.ACTIVE.value)

        with transaction.atomic():
            guild_link = super().create(validated_data)
            self._assign_role(guild_link.user, role_title, actor_user_id)
            return guild_link

    def update(self, instance, validated_data):
        actor_user_id = self.context.get('user_id')
        role_title = validated_data.pop('role', None)

        validated_data['updated_by_id'] = actor_user_id

        old_status = instance.status
        new_status = validated_data.get('status', old_status)

        # Clear previous_status when coming back from ON_LEAVE
        if old_status == InternGuildStatus.ON_LEAVE.value and new_status != InternGuildStatus.ON_LEAVE.value:
            validated_data['previous_status'] = None

        with transaction.atomic():
            guild_link = super().update(instance, validated_data)

            if new_status == InternGuildStatus.INACTIVE.value:
                # Revoke all intern roles on deactivation
                UserRoleLink.objects.filter(
                    user=guild_link.user,
                    role__title__in=[RoleType.INTERN.value, RoleType.INTERN_LEAD.value]
                ).delete()
            elif role_title:
                # Admin explicitly changing the role
                self._assign_role(guild_link.user, role_title, actor_user_id)

            return guild_link
