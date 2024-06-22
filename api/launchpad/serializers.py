import uuid

from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField, Q

from rest_framework import serializers

from db.user import User
from db.organization import UserOrganizationLink, Organization
from db.task import KarmaActivityLog
from db.launchpad import LaunchPadUsers, LaunchPadUserCollegeLink
from utils.types import LaunchPadRoles
from utils.utils import DateTimeUtils


class LaunchpadLeaderBoardSerializer(serializers.ModelSerializer):
    rank = serializers.SerializerMethodField()
    karma = serializers.IntegerField()
    actual_karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    org = serializers.CharField(allow_null=True, allow_blank=True)
    district_name = serializers.CharField(allow_null=True, allow_blank=True)
    state = serializers.CharField(allow_null=True, allow_blank=True)

    class Meta:
        model = User
        fields = ("rank", "full_name", "actual_karma", "karma", "org", "district_name", "state")

    def get_rank(self, obj):
        total_karma_subquery = KarmaActivityLog.objects.filter(
            user=OuterRef('id'),
            task__event='launchpad',
            appraiser_approved=True,
        ).values('user').annotate(
            total_karma=Sum('karma')
        ).values('total_karma')
        allowed_org_types = ["College", "School", "Company"]

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event='launchpad',
            appraiser_approved=True,
            task__hashtag='#lp24-introduction',
        ).values('user')
        
        users = User.objects.filter(
            karma_activity_log_user__task__event="launchpad",
            karma_activity_log_user__appraiser_approved=True,
            id__in=intro_task_completed_users
        ).prefetch_related(
            Prefetch(
                "user_organization_link_user",
                queryset=UserOrganizationLink.objects.filter(org__org_type__in=allowed_org_types),
            )
        ).filter(
            Q(user_organization_link_user__id__in=UserOrganizationLink.objects.filter(
                org__org_type__in=allowed_org_types
            ).values("id")) | Q(user_organization_link_user__id__isnull=True)
        ).annotate(
            karma=Subquery(total_karma_subquery, output_field=IntegerField()),
            time_=Max("karma_activity_log_user__created_at"),
        ).order_by("-karma", "time_")
        
        # high complexity
        rank = 0
        for data in users:
            rank += 1
            if data.id == obj.id:
                break    
        
        return rank


class LaunchpadParticipantsSerializer(serializers.ModelSerializer):
    org = serializers.CharField(allow_null=True, allow_blank=True)
    district_name = serializers.CharField(allow_null=True, allow_blank=True)
    state = serializers.CharField(allow_null=True, allow_blank=True)
    level = serializers.CharField(allow_null=True, allow_blank=True)

    class Meta:
        model = User
        fields = ("full_name", "level", "org", "district_name", "state")


class CollegeDataSerializer(serializers.ModelSerializer):
    district_name = serializers.CharField()
    state = serializers.CharField()
    total_users = serializers.IntegerField()
    level1 = serializers.IntegerField()
    level2 = serializers.IntegerField()
    level3 = serializers.IntegerField()
    level4 = serializers.IntegerField()
    
    class Meta:
        model = Organization
        fields = (
            "title", 
            "district_name", 
            "state", 
            "total_users", 
            "level1", 
            "level2",
            "level3", 
            "level4"
        )

class LaunchpadUserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(max_length=36, read_only=True)
    role = serializers.ChoiceField(choices=LaunchPadRoles.get_all_values())
    college = serializers.ListField(child=serializers.CharField(), allow_empty=True, write_only=True)
    colleges = serializers.SerializerMethodField()

    class Meta:
        model = LaunchPadUsers
        fields = ("id", "full_name", "email", "phone_number", "role", "college", "district", "zone", "colleges")

    def create(self, validated_data):
        validated_data.pop("college")
        
        validated_data["id"] = uuid.uuid4()
        validated_data["created_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()
        user = LaunchPadUsers.objects.create(**validated_data)
        
        return user

    def get_colleges(self, obj):
        return LaunchPadUserCollegeLink.objects.filter(user=obj).values_list("college_id", "college__title")


class LaunchpadUpdateUserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=LaunchPadRoles.get_all_values())
    remove_colleges = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    add_colleges = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    
    class Meta:
        model = LaunchPadUsers
        fields = ("full_name", "email", "phone_number", "role", "district", "zone", "remove_colleges", "add_colleges")
    
    def update(self, instance, validated_data):
        auth_user = self.context.get("auth_user")
        user_id = instance.id
        remove_colleges = validated_data.pop("remove_colleges")
        add_colleges = validated_data.pop("add_colleges")
        
        instance.full_name = validated_data.get("full_name", instance.full_name)
        instance.email = validated_data.get("email", instance.email)
        instance.phone_number = validated_data.get("phone_number", instance.phone_number)
        instance.role = validated_data.get("role", instance.role)
        instance.district = validated_data.get("district", instance.district)
        instance.zone = validated_data.get("zone", instance.zone)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        
        if remove_colleges:
            LaunchPadUserCollegeLink.objects.filter(college_id__in=remove_colleges, user_id=user_id).delete()
        
        if add_colleges:
            LaunchPadUserCollegeLink.objects.filter(college_id__in=add_colleges).delete()
            LaunchPadUserCollegeLink.objects.bulk_create([
                LaunchPadUserCollegeLink(
                    id=uuid.uuid4(),
                    user=instance,
                    college_id=college_id,
                    created_at=DateTimeUtils.get_current_utc_time(),
                    updated_at=DateTimeUtils.get_current_utc_time(),
                    created_by=auth_user,
                    updated_by=auth_user
                ) for college_id in add_colleges if Organization.objects.filter(id=college_id).exists()
            ])
        
        return instance
        

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(max_length=36, read_only=True)
    colleges = serializers.SerializerMethodField()

    class Meta:
        model = LaunchPadUsers
        fields = ("id", "full_name", "phone_number", "district", "zone", "email")

    def update(self, instance, validated_data):
        instance.full_name = validated_data.get("full_name", instance.full_name)
        instance.phone_number = validated_data.get("phone_number", instance.phone_number)
        instance.district = validated_data.get("district", instance.district)
        instance.zone = validated_data.get("zone", instance.zone)
        instance.email = validated_data.get("email", instance.email)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def get_colleges(self, obj):
        return LaunchPadUserCollegeLink.objects.filter(user=obj).values_list("college_id", "college__title")