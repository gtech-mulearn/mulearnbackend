import uuid

from django.db import transaction
from rest_framework import serializers

from db.user import User, UserMentor
from db.task import (
    KarmaActivityLog,
    MentorshipSession, MentorshipSessionUserLink,
)


class MentorStatusSerializer(serializers.ModelSerializer):
    is_mentor = serializers.SerializerMethodField()

    class Meta:
        model = UserMentor
        fields = [
            "is_mentor",
            "is_verified",
            "mentor_tier",
            "hours",
            "about",
            "expertise",
            "reason",
            "verified_at",
            "verification_note",
        ]

    def get_is_mentor(self, obj):
        return True


class MentorProfileUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = UserMentor
        fields = ["about", "expertise", "reason", "hours"]
        extra_kwargs = {
            "about": {"required": False},
            "expertise": {"required": False},
            "reason": {"required": False},
            "hours": {"required": False},
        }

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")
        instance.about = validated_data.get("about", instance.about)
        instance.expertise = validated_data.get("expertise", instance.expertise)
        instance.reason = validated_data.get("reason", instance.reason)
        instance.hours = validated_data.get("hours", instance.hours)
        instance.updated_by_id = user_id
        instance.save()
        return instance


class MentorSessionCreateSerializer(serializers.Serializer):
    mentee_id = serializers.CharField()
    ig_id = serializers.CharField(required=False, allow_null=True)
    title = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    mode = serializers.ChoiceField(
        choices=MentorshipSession.Mode.choices,
        default=MentorshipSession.Mode.ONLINE,
        required=False,
    )
    starts_at = serializers.DateTimeField()
    ends_at = serializers.DateTimeField()
    meeting_link = serializers.CharField(required=False, allow_null=True, max_length=500)

    def validate_mentee_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("Mentee not found")
        return value

    def validate(self, data):
        if data["ends_at"] <= data["starts_at"]:
            raise serializers.ValidationError(
                {"ends_at": "ends_at must be greater than starts_at"}
            )
        return data

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        mentee_id = validated_data.pop("mentee_id")
        ig_id = validated_data.pop("ig_id", None)

        with transaction.atomic():
            session = MentorshipSession.objects.create(
                id=str(uuid.uuid4()),
                ig_id=ig_id,
                title=validated_data["title"],
                description=validated_data.get("description"),
                mode=validated_data.get("mode", MentorshipSession.Mode.ONLINE),
                starts_at=validated_data["starts_at"],
                ends_at=validated_data["ends_at"],
                meeting_link=validated_data.get("meeting_link"),
                status=MentorshipSession.Status.SCHEDULED,
                created_by_id=user_id,
                updated_by_id=user_id,
            )

            MentorshipSessionUserLink.objects.create(
                id=str(uuid.uuid4()),
                session=session,
                user_id=user_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTOR,
                attendance_status=MentorshipSessionUserLink.AttendanceStatus.INVITED,
            )

            MentorshipSessionUserLink.objects.create(
                id=str(uuid.uuid4()),
                session=session,
                user_id=mentee_id,
                participant_role=MentorshipSessionUserLink.ParticipantRole.MENTEE,
                attendance_status=MentorshipSessionUserLink.AttendanceStatus.INVITED,
            )

        return session


class SessionParticipantSerializer(serializers.Serializer):
    user_id = serializers.CharField(source="user.id")
    full_name = serializers.CharField(source="user.full_name")
    participant_role = serializers.CharField()
    attendance_status = serializers.CharField()


class MentorSessionListSerializer(serializers.ModelSerializer):
    ig_name = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    class Meta:
        model = MentorshipSession
        fields = [
            "id",
            "ig_name",
            "title",
            "mode",
            "starts_at",
            "ends_at",
            "status",
            "meeting_link",
            "participants",
        ]

    def get_ig_name(self, obj):
        return obj.ig.name if obj.ig else None

    def get_participants(self, obj):
        links = obj.session_user_links.select_related("user").all()
        return SessionParticipantSerializer(links, many=True).data


class ParticipantUpdateSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    participant_role = serializers.ChoiceField(
        choices=MentorshipSessionUserLink.ParticipantRole.choices,
        required=False,
    )
    attendance_status = serializers.ChoiceField(
        choices=MentorshipSessionUserLink.AttendanceStatus.choices,
        required=False,
    )
    progress_note = serializers.CharField(max_length=500, required=False, allow_null=True)
    contributed_minutes = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class MentorSessionUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            MentorshipSession.Status.COMPLETED,
            MentorshipSession.Status.CANCELLED,
            MentorshipSession.Status.NO_SHOW,
        ],
        required=False,
    )
    participants = ParticipantUpdateSerializer(many=True, required=False)

    def update(self, instance, validated_data):
        user_id = self.context.get("user_id")

        if "status" in validated_data:
            instance.status = validated_data["status"]

        instance.updated_by_id = user_id
        instance.save()

        if "participants" in validated_data:
            for p in validated_data["participants"]:
                p_user_id = p.get("user_id")
                if not p_user_id:
                    continue

                filters = {"session": instance, "user_id": p_user_id}
                if "participant_role" in p:
                    filters["participant_role"] = p["participant_role"]

                link = MentorshipSessionUserLink.objects.filter(**filters).first()
                if link:
                    if "attendance_status" in p:
                        link.attendance_status = p["attendance_status"]
                    if "progress_note" in p:
                        link.progress_note = p["progress_note"]
                    if "contributed_minutes" in p:
                        link.contributed_minutes = p["contributed_minutes"]
                    link.save()

        return instance


class TaskQueueSerializer(serializers.ModelSerializer):
    mentee_id = serializers.CharField(source="user.id")
    mentee_name = serializers.CharField(source="user.full_name")
    task_id = serializers.CharField(source="task.id")
    task_title = serializers.CharField(source="task.title")
    task_hashtag = serializers.CharField(source="task.hashtag")
    task_karma = serializers.IntegerField(source="task.karma")
    ig_name = serializers.SerializerMethodField()

    class Meta:
        model = KarmaActivityLog
        fields = [
            "id",
            "mentee_id",
            "mentee_name",
            "task_id",
            "task_title",
            "task_hashtag",
            "task_karma",
            "ig_name",
            "mentor_review_status",
            "mentor_review_feedback",
            "created_at",
        ]

    def get_ig_name(self, obj):
        if obj.task and obj.task.ig:
            return obj.task.ig.name
        return None
