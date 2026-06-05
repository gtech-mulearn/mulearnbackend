import uuid
from rest_framework import serializers

from db.user import UserMentor, UserRoleLink, Role
from db.task import InterestGroup, UserIgLink
from utils.types import RoleType
from utils.utils import DateTimeUtils

class MentorRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMentor
        fields = [
            "about",
            "expertise",
            "reason",
            "hours",
            "preferred_ig_ids"
        ]

    def validate_preferred_ig_ids(self, value):
        if not value or not isinstance(value, list) or len(value) == 0:
            raise serializers.ValidationError("At least one preferred IG ID must be provided.")
        for ig_id in value:
            if not InterestGroup.objects.filter(id=ig_id).exists():
                raise serializers.ValidationError(f"Invalid IG ID: {ig_id}")
        return value

    def create(self, validated_data):
        user_id = self.context["user_id"]
        
        mentor = UserMentor.objects.create(
            user_id=user_id,
            status=UserMentor.Status.PENDING,
            mentor_tier=UserMentor.MentorTier.IG_MENTOR,
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=DateTimeUtils.get_current_utc_time(),
            updated_at=DateTimeUtils.get_current_utc_time(),
            **validated_data
        )
        return mentor

class MentorUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMentor
        fields = [
            "about",
            "expertise",
            "reason",
            "hours",
            "preferred_ig_ids"
        ]

    def validate_preferred_ig_ids(self, value):
        if value:
            if not isinstance(value, list) or len(value) == 0:
                raise serializers.ValidationError("At least one preferred IG ID must be provided.")
            for ig_id in value:
                if not InterestGroup.objects.filter(id=ig_id).exists():
                    raise serializers.ValidationError(f"Invalid IG ID: {ig_id}")
        return value

    def update(self, instance, validated_data):
        validated_data['updated_at'] = DateTimeUtils.get_current_utc_time()
        validated_data['updated_by_id'] = self.context.get("user_id", instance.user_id)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

class MentorListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserMentor
        fields = [
            "id",
            "user_id",
            "user_full_name",
            "user_email",
            "mentor_tier",
            "status",
            "created_at",
            "updated_at"
        ]

class MentorDetailSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserMentor
        fields = "__all__"

class MentorVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[UserMentor.Status.APPROVED, UserMentor.Status.REJECTED])
    verification_note = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        if data.get("status") == UserMentor.Status.REJECTED and not data.get("verification_note"):
            raise serializers.ValidationError("Verification note is required when rejecting.")
        return data

    def update(self, instance, validated_data):
        user_id = self.context["user_id"]
        status = validated_data.get("status")
        
        instance.status = status
        instance.updated_by_id = user_id
        instance.updated_at = DateTimeUtils.get_current_utc_time()
        
        if status == UserMentor.Status.APPROVED:
            instance.verified_by_id = user_id
            instance.verified_at = DateTimeUtils.get_current_utc_time()
            
            # Assign global MENTOR role
            mentor_role = Role.objects.filter(title=RoleType.MENTOR.value).first()
            if mentor_role:
                role_link, created = UserRoleLink.objects.get_or_create(
                    user=instance.user,
                    role=mentor_role,
                    defaults={
                        "verified": True,
                        "created_by_id": user_id,
                        "created_at": DateTimeUtils.get_current_utc_time(),
                    },
                )
                if not created and not role_link.verified:
                    role_link.verified = True
                    role_link.save(update_fields=["verified"])

            # Auto-assign UserIgLink for IG_MENTOR
            if instance.mentor_tier == UserMentor.MentorTier.IG_MENTOR and instance.preferred_ig_ids:
                for ig_id in instance.preferred_ig_ids:
                    ig = InterestGroup.objects.filter(id=ig_id).first()
                    if ig:
                        ig_link, created = UserIgLink.objects.get_or_create(
                            user=instance.user,
                            ig=ig,
                            defaults={
                                "assignment_type": UserIgLink.AssignmentType.MENTOR,
                                "is_active": True,
                                "assigned_by_id": user_id,
                                "created_by_id": user_id,
                                "created_at": DateTimeUtils.get_current_utc_time(),
                            },
                        )
                        if not created:
                            ig_link.assignment_type = UserIgLink.AssignmentType.MENTOR
                            ig_link.is_active = True
                            ig_link.assigned_by_id = user_id
                            ig_link.save(
                                update_fields=["assignment_type", "is_active", "assigned_by_id"]
                            )

            # Auto-link COMPANY_MENTOR to the company's Organization
            if instance.mentor_tier == UserMentor.MentorTier.COMPANY_MENTOR and instance.org:
                from db.organization import UserOrganizationLink
                org_link, created = UserOrganizationLink.objects.get_or_create(
                    user=instance.user,
                    org=instance.org,
                    defaults={
                        "verified": True,
                        "created_by_id": user_id,
                        "created_at": DateTimeUtils.get_current_utc_time(),
                    },
                )
                if not created and not org_link.verified:
                    org_link.verified = True
                    org_link.save(update_fields=["verified"])

        elif status == UserMentor.Status.REJECTED:
            instance.verification_note = validated_data.get("verification_note")
            
        instance.save()
        return instance


from db.mentor import MentorshipSession
from db.organization import Organization
from db.task import InterestGroup
from .session_recurrence_helper import generate_recurring_sessions

class SessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        fields = [
            "entity_id",
            "session_type",
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "max_participants",
            "is_recurring",
            "recurrence_type",
            "recurrence_interval",
            "recurrence_end_date"
        ]

    def validate(self, data):
        user_id = self.context.get("user_id")
        if MentorshipSession.objects.filter(
            title=data.get('title'),
            starts_at=data.get('starts_at'),
            entity_id=data.get('entity_id'),
            created_by_id=user_id,
            is_deleted=False
        ).exists():
            raise serializers.ValidationError("A session with this exact title and start time already exists.")

        if data.get('starts_at') >= data.get('ends_at'):
            raise serializers.ValidationError("Session start time must be before end time.")
            
        is_recurring = data.get('is_recurring', False)
        if is_recurring:
            if not data.get('recurrence_type'):
                raise serializers.ValidationError("recurrence_type is required when is_recurring is true.")
            if not data.get('recurrence_interval') or data.get('recurrence_interval') < 1:
                raise serializers.ValidationError("recurrence_interval must be a positive integer.")
            if not data.get('recurrence_end_date'):
                raise serializers.ValidationError("recurrence_end_date is required when is_recurring is true.")
            if data.get('recurrence_end_date') <= data.get('starts_at').date():
                raise serializers.ValidationError("recurrence_end_date must be after the session starts_at date.")
                
        return data

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        
        session = MentorshipSession.objects.create(
            status=MentorshipSession.Status.PENDING_APPROVAL,
            created_by_id=user_id,
            updated_by_id=user_id,
            **validated_data
        )
        
        if session.is_recurring:
            generate_recurring_sessions(session)
            
        return session

class SessionUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSession
        fields = [
            "title",
            "description",
            "mode",
            "starts_at",
            "ends_at",
            "meeting_link",
            "venue",
            "max_participants"
        ]

    def validate(self, data):
        # Allow partial updates by fetching from instance if not in data
        starts_at = data.get('starts_at', self.instance.starts_at) if self.instance else data.get('starts_at')
        ends_at = data.get('ends_at', self.instance.ends_at) if self.instance else data.get('ends_at')
        
        if starts_at and ends_at and starts_at >= ends_at:
            raise serializers.ValidationError("Session start time must be before end time.")
        return data

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        
        # If edited after being SCHEDULED, revert to PENDING_APPROVAL
        if instance.status == MentorshipSession.Status.SCHEDULED:
            instance.status = MentorshipSession.Status.PENDING_APPROVAL
            
        instance.updated_by_id = user_id
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance

class SessionListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    entity_name = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "entity_id",
            "entity_name",
            "session_type",
            "title",
            "mode",
            "starts_at",
            "ends_at",
            "status",
            "created_by_id",
            "created_by_name",
            "created_at",
            "max_participants"
        ]

    def get_entity_name(self, obj):
        if obj.session_type == MentorshipSession.SessionType.IG_SESSION:
            ig = InterestGroup.objects.filter(id=obj.entity_id).first()
            return ig.name if ig else None
        elif obj.session_type in (
            MentorshipSession.SessionType.CAMPUS_SESSION,
            MentorshipSession.SessionType.COMPANY_SESSION,
        ):
            org = Organization.objects.filter(id=obj.entity_id).first()
            return org.title if org else None
        return None

class SessionDetailSerializer(SessionListSerializer):
    class Meta(SessionListSerializer.Meta):
        fields = SessionListSerializer.Meta.fields + [
            "description",
            "meeting_link",
            "venue"
        ]

class AdminSessionVerifySerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        MentorshipSession.Status.SCHEDULED, 
        MentorshipSession.Status.REJECTED
    ])

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        status = validated_data.get("status")
        
        instance.status = status
        instance.updated_by_id = user_id
        
        if status == MentorshipSession.Status.SCHEDULED:
            instance.approved_by_id = user_id
            instance.approved_at = DateTimeUtils.get_current_utc_time()
            
        instance.save()
        return instance

from db.mentor import MentorAvailabilitySlot

class AvailabilitySlotSerializer(serializers.ModelSerializer):
    ig_name = serializers.CharField(source='ig.name', read_only=True)
    
    class Meta:
        model = MentorAvailabilitySlot
        fields = [
            "id",
            "mentor_user_id",
            "ig_id",
            "ig_name",
            "weekday",
            "start_time",
            "end_time",
            "timezone",
            "is_active",
            "valid_from",
            "valid_to",
            "created_at",
            "updated_at"
        ]

class AvailabilitySlotCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorAvailabilitySlot
        fields = [
            "ig",
            "weekday",
            "start_time",
            "end_time",
            "timezone",
            "is_active",
            "valid_from",
            "valid_to"
        ]

    def validate(self, data):
        start_time = data.get('start_time', self.instance.start_time if self.instance else None)
        end_time = data.get('end_time', self.instance.end_time if self.instance else None)
        weekday = data.get('weekday', self.instance.weekday if self.instance else None)
        valid_from = data.get('valid_from', self.instance.valid_from if self.instance else None)
        valid_to = data.get('valid_to', self.instance.valid_to if self.instance else None)
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time.")
            
        if weekday and (weekday < 1 or weekday > 7):
            raise serializers.ValidationError("Weekday must be between 1 (Mon) and 7 (Sun).")
            
        if valid_from and valid_to and valid_from > valid_to:
            raise serializers.ValidationError("Valid from date must be before or equal to valid to date.")
            
        return data

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        
        slot = MentorAvailabilitySlot.objects.create(
            mentor_user_id=user_id,
            created_by_id=user_id,
            updated_by_id=user_id,
            **validated_data
        )
        return slot

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.updated_by_id = user_id
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        instance.save()
        return instance

from db.mentor import MentorshipSessionUserLink

class ParticipantJoinSerializer(serializers.Serializer):
    def create(self, validated_data):
        user_id = self.context.get("user_id")
        session_id = self.context.get("session_id")
        
        session = MentorshipSession.objects.filter(id=session_id).first()
        if not session:
            raise serializers.ValidationError("Session not found.")
            
        if session.status != MentorshipSession.Status.SCHEDULED:
            raise serializers.ValidationError("Only scheduled sessions can be joined.")
            
        if session.max_participants:
            current_count = MentorshipSessionUserLink.objects.filter(session_id=session_id).count()
            if current_count >= session.max_participants:
                raise serializers.ValidationError("Session has reached its maximum participant limit.")
                
        if MentorshipSessionUserLink.objects.filter(session_id=session_id, user_id=user_id).exists():
            raise serializers.ValidationError("You have already joined this session.")
            
        link = MentorshipSessionUserLink.objects.create(
            session_id=session_id,
            user_id=user_id,
            participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
            attendance_status=MentorshipSessionUserLink.AttendanceStatus.INVITED
        )
        return link

class ParticipantListSerializer(serializers.ModelSerializer):
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    mu_id = serializers.CharField(source='user.mu_id', read_only=True)
    
    class Meta:
        model = MentorshipSessionUserLink
        fields = [
            "id",
            "session_id",
            "user_id",
            "user_full_name",
            "mu_id",
            "participant_role",
            "attendance_status",
            "progress_note",
            "feedback",
            "contributed_minutes",
            "created_at"
        ]

class ParticipantUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSessionUserLink
        fields = [
            "attendance_status",
            "progress_note",
            "contributed_minutes"
        ]

    def validate(self, data):
        contributed_minutes = data.get('contributed_minutes')
        if contributed_minutes is not None and contributed_minutes <= 0:
            raise serializers.ValidationError("Contributed minutes must be greater than zero.")
        return data

class ParticipantFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = MentorshipSessionUserLink
        fields = ["feedback"]

    def validate(self, data):
        if not data.get("feedback"):
            raise serializers.ValidationError("Feedback cannot be empty.")
            
        if self.instance.attendance_status != MentorshipSessionUserLink.AttendanceStatus.ATTENDED:
            raise serializers.ValidationError("You can only leave feedback for sessions you have attended.")
            
        return data

class MentorActivitySerializer(serializers.Serializer):
    id = serializers.CharField()
    activity_type = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True, required=False)
    date = serializers.DateTimeField()
    status = serializers.CharField(allow_null=True, required=False)

