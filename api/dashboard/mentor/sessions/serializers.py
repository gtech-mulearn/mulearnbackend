import uuid

from django.db import transaction
from rest_framework import serializers

from db.user import User, UserMentor
from db.mentor import MentorshipSession, MentorshipSessionUserLink


class MentorSessionCreateSerializer(serializers.Serializer):
    mentee_id = serializers.CharField()
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
        user_id = self.context.get("user_id")
        if value == user_id:
            raise serializers.ValidationError("You cannot schedule a session with yourself")
        return value

    def validate(self, data):
        if data["ends_at"] <= data["starts_at"]:
            raise serializers.ValidationError(
                {"ends_at": "ends_at must be after starts_at"}
            )
        return data

    def create(self, validated_data):
        user_id = self.context.get("user_id")
        # ig_id is injected from the active persona context — not supplied by client
        ig_id = self.context.get("ig_id")
        mentee_id = validated_data.pop("mentee_id")

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
        # related_name on MentorshipSessionUserLink.session is 'participants'
        links = obj.participants.select_related("user").all()
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
