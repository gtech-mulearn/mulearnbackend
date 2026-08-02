from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from .serializers import MentorDeactivationSerializer
from db.user import UserMentor
from db.mentor import SystemActionLog
from api.notification.notifications_utils import NotificationUtils
from django.conf import settings


class MentorDeactivationAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Admin"],
        description="Deactivates a mentor's account, preventing them from using mentor privileges.",
        request=MentorDeactivationSerializer,
        responses={200: {}}
    )
    @role_required([RoleType.ADMIN.value])
    def post(self, request, user_mentor_id):
        admin_id = JWTUtils.fetch_user_id(request)

        mentor_profile = UserMentor.objects.filter(id=user_mentor_id).select_related('user').first()
        if not mentor_profile:
            return CustomResponse(general_message="Mentor profile not found.").get_failure_response(status_code=404)

        if not mentor_profile.is_active:
            return CustomResponse(general_message="Mentor is already deactivated.").get_failure_response(status_code=400)

        serializer = MentorDeactivationSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        reason = serializer.validated_data.get("reason")

        mentor_profile.is_active = False
        mentor_profile.updated_by_id = admin_id
        mentor_profile.save(update_fields=["is_active", "updated_by_id", "updated_at"])

        # Log the action
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.MENTOR_DEACTIVATE,
            actor_user_id=admin_id,
            subject_user=mentor_profile.user,
            entity_name='user_mentor',
            entity_id=mentor_profile.id,
            new_data={'is_active': False, 'reason': reason},
            remarks=f"Mentor {mentor_profile.user.full_name} deactivated by admin. Reason: {reason}"
        )

        # Notify the mentor
        try:
            NotificationUtils.insert_notification(
                user=mentor_profile.user,
                title="Your Mentor Account has been Deactivated",
                description=f"Your mentor account has been temporarily deactivated by an administrator. Reason: {reason}",
                button="Contact Support",
                url=f"{settings.FR_DOMAIN_NAME}/contact-us",
                created_by_id=admin_id,
            )
        except Exception:
            pass

        return CustomResponse(general_message="Mentor deactivated successfully.").get_success_response()


class MentorReactivationAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Admin"],
        description="Reactivates a previously deactivated mentor's account.",
        responses={200: {}}
    )
    @role_required([RoleType.ADMIN.value])
    def post(self, request, user_mentor_id):
        admin_id = JWTUtils.fetch_user_id(request)

        mentor_profile = UserMentor.objects.filter(id=user_mentor_id).select_related('user').first()
        if not mentor_profile:
            return CustomResponse(general_message="Mentor profile not found.").get_failure_response(status_code=404)

        if mentor_profile.is_active:
            return CustomResponse(general_message="Mentor is already active.").get_failure_response(status_code=400)

        mentor_profile.is_active = True
        mentor_profile.updated_by_id = admin_id
        mentor_profile.save(update_fields=["is_active", "updated_by_id", "updated_at"])

        # Log the action
        SystemActionLog.objects.create(
            action_type=SystemActionLog.ActionType.MENTOR_REACTIVATE,
            actor_user_id=admin_id,
            subject_user=mentor_profile.user,
            entity_name='user_mentor',
            entity_id=mentor_profile.id,
            new_data={'is_active': True},
            remarks=f"Mentor {mentor_profile.user.full_name} reactivated by admin."
        )

        # Notify the mentor
        try:
            NotificationUtils.insert_notification(
                user=mentor_profile.user,
                title="Your Mentor Account has been Reactivated",
                description="Your mentor account has been reactivated. You can now resume your mentor activities.",
                button="Go to Dashboard",
                url=f"{settings.FR_DOMAIN_NAME}/dashboard",
                created_by_id=admin_id,
            )
        except Exception:
            pass

        return CustomResponse(general_message="Mentor reactivated successfully.").get_success_response()