import uuid
from django.db.models import Sum, Max, Prefetch, F, OuterRef, Subquery, IntegerField, Q
from rest_framework import serializers
from db.user import User
from db.organization import UserOrganizationLink, Organization
from db.task import KarmaActivityLog
from db.launchpad import LaunchPadUsers, LaunchPadUserCollegeLink, LaunchPad, LaunchpadJobTasks
from utils.types import LaunchPadRoles
from utils.utils import DateTimeUtils
from utils.types import  OrganizationType
from db.launchpad import LaunchpadCompanies, LaunchpadRecruiters, LaunchpadJobs , LaunchpadJobApplications
from db.task import (
    KarmaActivityLog,
    Wallet
)

class LaunchpadCompaniesSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaunchpadCompanies
        fields = [
            'id', 'name', 'poc_name', 'poc_role', 'poc_email', 'website' , 'description', 'address',
            'poc_phone', 'username', 'password','is_verified', 'created_at', 'updated_at'
        ]

class LaunchpadRecruiterSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaunchpadRecruiters
        fields = [
            'id', 'company', 'name', 'email', 
            'phone', 'password', 'role', 'created_at', 'updated_at'
        ]

class LaunchpadJobsSerializer(serializers.ModelSerializer):
    skills = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    experience = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    task = serializers.PrimaryKeyRelatedField(
        queryset=LaunchpadJobTasks.objects.all(), required=False, allow_null=True
    )
    opening_type = serializers.CharField(required=False, allow_blank=True, allow_null=True, default="General")
    
    class Meta:
        model = LaunchpadJobs
        fields = [
            'id', 'company', 'recruiter', 'title', 'skills', 'experience', 'domain', 'opening_type','location','salary_range','job_type', 'minimum_karma',
            'interest_groups', 'task', 'created_at', 'updated_at'
        ]

class TaskVerificationSerializer(serializers.Serializer):
    task_id = serializers.CharField(required=True)
    hashtag = serializers.CharField(required=True)
    is_verified = serializers.BooleanField(default=True)
    
    def validate_hashtag(self, value):
        if not value.startswith('#'):
            raise serializers.ValidationError("Hashtag must start with '#'")
        return value
    
    def validate_task_id(self, value):
        if not LaunchpadJobTasks.objects.filter(id=value).exists():
            raise serializers.ValidationError("Task not found")
        return value
    
    def save(self):
        task_id = self.validated_data['task_id']
        hashtag = self.validated_data['hashtag']  
        
        task = LaunchpadJobTasks.objects.get(id=task_id)
        task.hashtags = hashtag
        task.is_verified = True  
        task.save()
        
        return task

class LaunchpadJobTaskSerializer(serializers.ModelSerializer):
    hashtags = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)

    class Meta:
        model = LaunchpadJobTasks
        fields = [
            'id', 'task_description', 'hashtags', 'is_verified', 'created_at', 'updated_at'
        ]

class EligibleStudentSerializer(serializers.ModelSerializer):
    karma = serializers.IntegerField(source='wallet_user.karma', default=0)
    level = serializers.CharField(source='user_lvl_link_user.level.name', default=None)
    college_name = serializers.SerializerMethodField()
    interest_groups = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    karma_distribution = serializers.SerializerMethodField()
    application_status = serializers.SerializerMethodField()
    application_timeline = serializers.SerializerMethodField()
    candidate_links = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'muid', 'profile_pic',
            'karma', 'level', 'college_name', 'interest_groups', 
            'roles', 'rank', 'karma_distribution', 'application_status',
            'application_timeline', 'candidate_links'
        ]
    
    def get_college_name(self, obj):
        college_link = obj.user_organization_link_user.filter(
            org__org_type='College'
        ).first()
        return college_link.org.title if college_link else None
    
    def get_interest_groups(self, obj):
        return [
            {
                'id': ig_link.ig.id,
                'name': ig_link.ig.name
            }
            for ig_link in obj.user_ig_link_user.all()
        ]
    
    def get_roles(self, obj):
        return [link.role.title for link in obj.user_role_link_user.all()]
    
    def get_rank(self, obj):
        # Get rank from context
        ranks = self.context.get('ranks', {})
        return ranks.get(obj.id, None)
    
    def get_application_status(self, obj):
        # Get application status from context
        application_status_map = self.context.get('application_status_map', {})
        if obj.id in application_status_map:
            return application_status_map[obj.id]['status']
        return 'not_invited'  # Student hasn't been invited yet
    
    def get_application_timeline(self, obj):
        # Get application timeline from context
        application_status_map = self.context.get('application_status_map', {})
        if obj.id in application_status_map:
            return {
                'invited_at': application_status_map[obj.id]['invited_at'],
                'applied_at': application_status_map[obj.id]['applied_at']
            }
        return None
    
    def get_candidate_links(self, obj):
        # Get candidate links from context if they've applied
        application_status_map = self.context.get('application_status_map', {})
        
        if obj.id in application_status_map:
            status = application_status_map[obj.id]['status']
            # Only return links if student has applied (not just invited)
            if status in ['applied', 'interview_scheduled', 'accepted', 'rejected']:
                # Get the full application details
                job = self.context.get('job')
                if job:
                    try:
                        application = LaunchpadJobApplications.objects.get(
                            job=job, 
                            student_id=obj.id
                        )
                        return {
                            'resume_link': application.resume_link,
                            'linkedin_link': application.linkedin_link,
                            'portfolio_link': application.portfolio_link,
                            'cover_letter': application.cover_letter,
                            'other_link': application.other_link,
                            'links_available': bool(
                                application.resume_link or 
                                application.linkedin_link or 
                                application.portfolio_link or 
                                application.cover_letter or 
                                application.other_link
                            )
                        }
                    except LaunchpadJobApplications.DoesNotExist:
                        pass
        
        return {
            'resume_link': None,
            'linkedin_link': None,
            'portfolio_link': None,
            'cover_letter': None,
            'other_link': None,
            'links_available': False
        }
    
    def get_karma_distribution(self, obj):
        return (
            KarmaActivityLog.objects.filter(user=obj, appraiser_approved=True)
            .values(task_type=F('task__type__title'))
            .annotate(karma=Sum('karma'))
            .order_by()
        )
#<--------------------------------------------------- old launchpad ------------------------------------------------->
class LaunchPadIDSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaunchPad
        fields = ["launchpad_id"]

    def to_representation(self, instance):
        return instance.launchpad_id


class LaunchPadRankSerializer(serializers.ModelSerializer):
    launchpad_rank = serializers.SerializerMethodField("get_rank")

    class Meta:
        model = User
        fields = ["launchpad_rank"]

    def get_rank(self, obj):
        total_karma_subquery = (
            KarmaActivityLog.objects.filter(
                user=OuterRef("id"),
                task__event="launchpad",
                appraiser_approved=True,
            )
            .values("user")
            .annotate(total_karma=Sum("karma"))
            .values("total_karma")
        )

        intro_task_completed_users = KarmaActivityLog.objects.filter(
            task__event="launchpad",
            appraiser_approved=True,
            task__hashtag="#lp24-introduction",
        ).values("user")

        users = (
            User.objects.filter(
                karma_activity_log_user__task__event="launchpad",
                karma_activity_log_user__appraiser_approved=True,
                id__in=intro_task_completed_users,
            )
            .annotate(
                karma=Subquery(total_karma_subquery, output_field=IntegerField()),
                time_=Max("karma_activity_log_user__created_at"),
            )
            .order_by("-karma", "time_")
        )

        # high complexity
        rank = 0
        for data in users:
            rank += 1
            if data.id == obj.id:
                break

        return rank


class LaunchpadLeaderBoardSerializer(serializers.ModelSerializer):
    rank = serializers.IntegerField()
    karma = serializers.IntegerField()
    actual_karma = serializers.IntegerField(source="wallet_user.karma", default=None)
    org = serializers.CharField(allow_null=True, allow_blank=True)
    district_name = serializers.CharField(allow_null=True, allow_blank=True)
    state = serializers.CharField(allow_null=True, allow_blank=True)
    launchpad_id = LaunchPadIDSerializer(source="launchpad_user.first", read_only=True)

    class Meta:
        model = User
        fields = (
            "rank",
            "full_name",
            "actual_karma",
            "karma",
            "org",
            "district_name",
            "state",
            "launchpad_id",
        )


class TaskCompletedLeaderBoardSerializer(serializers.ModelSerializer):
    # rank = serializers.SerializerMethodField('get_rank')
    rank = serializers.IntegerField()
    karma = serializers.IntegerField()
    is_public = serializers.BooleanField(
        source="user_settings_user.is_public", default=False
    )
    org = serializers.CharField(allow_null=True, allow_blank=True)
    district_name = serializers.CharField(allow_null=True, allow_blank=True)
    state = serializers.CharField(allow_null=True, allow_blank=True)

    class Meta:
        model = User
        fields = (
            "muid",
            "is_public",
            "rank",
            "full_name",
            "karma",
            "org",
            "district_name",
            "state",
            "profile_pic",
        )

    def get_rank(self, obj):
        return getattr(obj, "rank", None)


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
            "id",
            "title",
            "district_name",
            "state",
            "total_users",
            "level1",
            "level2",
            "level3",
            "level4",
        )


class LaunchpadUserSerializer(serializers.ModelSerializer):
    id = serializers.CharField(max_length=36, read_only=True)
    role = serializers.ChoiceField(choices=LaunchPadRoles.get_all_values())
    colleges = serializers.ListField(
        child=serializers.CharField(), allow_empty=True, write_only=True
    )

    class Meta:
        model = LaunchPadUsers
        fields = (
            "id",
            "full_name",
            "email",
            "phone_number",
            "role",
            "district",
            "zone",
            "colleges",
        )

    def create(self, validated_data):
        validated_data.pop("colleges")

        validated_data["id"] = uuid.uuid4()
        validated_data["created_at"] = DateTimeUtils.get_current_utc_time()
        validated_data["updated_at"] = DateTimeUtils.get_current_utc_time()
        user = LaunchPadUsers.objects.create(**validated_data)

        return user


class LaunchpadUserListSerializer(serializers.ModelSerializer):
    colleges = serializers.SerializerMethodField()

    class Meta:
        model = LaunchPadUsers
        fields = (
            "id",
            "full_name",
            "email",
            "phone_number",
            "role",
            "district",
            "zone",
            "colleges",
        )

    def get_colleges(self, obj):
        return LaunchPadUserCollegeLink.objects.filter(user=obj).values_list(
            "college_id", "college__title"
        )


class LaunchpadUpdateUserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=LaunchPadRoles.get_all_values())
    remove_colleges = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )
    add_colleges = serializers.ListField(
        child=serializers.CharField(), allow_empty=True
    )

    class Meta:
        model = LaunchPadUsers
        fields = (
            "full_name",
            "email",
            "phone_number",
            "role",
            "district",
            "zone",
            "remove_colleges",
            "add_colleges",
        )

    def update(self, instance, validated_data):
        auth_user = self.context.get("auth_user")
        user_id = instance.id
        remove_colleges = validated_data.pop("remove_colleges")
        add_colleges = validated_data.pop("add_colleges")

        instance.full_name = validated_data.get("full_name", instance.full_name)
        instance.email = validated_data.get("email", instance.email)
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        instance.role = validated_data.get("role", instance.role)
        instance.district = validated_data.get("district", instance.district)
        instance.zone = validated_data.get("zone", instance.zone)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()

        if remove_colleges:
            LaunchPadUserCollegeLink.objects.filter(
                college_id__in=remove_colleges, user_id=user_id
            ).delete()

        if add_colleges:
            LaunchPadUserCollegeLink.objects.filter(
                college_id__in=add_colleges
            ).delete()
            LaunchPadUserCollegeLink.objects.bulk_create(
                [
                    LaunchPadUserCollegeLink(
                        id=uuid.uuid4(),
                        user=instance,
                        college_id=college_id,
                        created_at=DateTimeUtils.get_current_utc_time(),
                        updated_at=DateTimeUtils.get_current_utc_time(),
                        created_by=auth_user,
                        updated_by=auth_user,
                    )
                    for college_id in add_colleges
                    if Organization.objects.filter(id=college_id).exists()
                ]
            )

        return instance


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    id = serializers.CharField(max_length=36, read_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    district = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    zone = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    email = serializers.EmailField(required=False)
    colleges = serializers.SerializerMethodField()

    class Meta:
        model = LaunchPadUsers
        fields = (
            "id",
            "full_name",
            "phone_number",
            "district",
            "zone",
            "email",
            "colleges",
        )

    def validate(self, attrs):
        if (
            LaunchPadUsers.objects.filter(email=attrs.get("email"))
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise serializers.ValidationError("Email already exists")
        return super().validate(attrs)

    def update(self, instance, validated_data):
        instance.full_name = validated_data.get("full_name", instance.full_name)
        instance.phone_number = validated_data.get(
            "phone_number", instance.phone_number
        )
        instance.district = validated_data.get("district", instance.district)
        instance.zone = validated_data.get("zone", instance.zone)
        instance.email = validated_data.get("email", instance.email)
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        instance.save()
        return instance

    def get_colleges(self, obj):
        return LaunchPadUserCollegeLink.objects.filter(user=obj).values_list(
            "college_id", "college__title"
        )
