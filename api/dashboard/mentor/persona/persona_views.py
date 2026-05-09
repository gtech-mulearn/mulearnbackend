from django.utils import timezone
from rest_framework.views import APIView

from db.user import User, UserRoleLink, UserSettings, UserMentor
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from .serializers import PersonaSwitchSerializer, IGRoleItemSerializer


class PersonaSwitchView(APIView):
    """
    POST /api/v1/dashboard/mentor/persona/switch/

    Switches the authenticated user's active persona to 'mentor' for a
    specific IG role link. Writes state to user_settings (DB source of truth).
    """
    permission_classes = [CustomizePermission]

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User not found."
            ).get_failure_response()

        serializer = PersonaSwitchSerializer(
            data=request.data, context={'user': user}
        )
        if not serializer.is_valid():
            return CustomResponse(
                general_message="Invalid persona switch request.",
                message=serializer.errors,
            ).get_failure_response()

        role_link = serializer.validated_data['role_link']
        ig = role_link.ig

        # Atomic write to user_settings
        user_settings, _ = UserSettings.objects.get_or_create(
            user=user,
            defaults={
                'created_by': user,
                'updated_by': user,
            }
        )
        user_settings.active_persona = UserSettings.PersonaType.MENTOR
        user_settings.active_role_link = role_link
        user_settings.active_ig = ig
        user_settings.last_persona_switched_at = timezone.now()
        user_settings.updated_by = user
        user_settings.save(update_fields=[
            'active_persona', 'active_role_link', 'active_ig',
            'last_persona_switched_at', 'updated_by', 'updated_at',
        ])

        mentor_profile = UserMentor.objects.filter(user=user).first()

        return CustomResponse(
            general_message="Persona switched to mentor successfully.",
            response={
                "active_persona": "mentor",
                "active_role_link_id": str(role_link.id),
                "active_ig_id": str(ig.id),
                "ig_name": ig.name,
                "is_verified": mentor_profile.is_verified if mentor_profile else False,
                "mentor_tier": mentor_profile.mentor_tier if mentor_profile else "NORMAL",
                "last_persona_switched_at": user_settings.last_persona_switched_at.isoformat(),
                # JWT reissue is optional; key always present for schema consistency
                "access": None,
            }
        ).get_success_response()


class PersonaResetView(APIView):
    """
    POST /api/v1/dashboard/mentor/persona/reset/

    Resets the active persona to 'learner'. Clears IG and role_link context.
    """
    permission_classes = [CustomizePermission]

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(
                general_message="User not found."
            ).get_failure_response()

        user_settings = UserSettings.objects.filter(user=user).first()
        if not user_settings:
            return CustomResponse(
                general_message="User settings not found."
            ).get_failure_response()

        user_settings.active_persona = UserSettings.PersonaType.LEARNER
        user_settings.active_role_link = None
        user_settings.active_ig = None
        user_settings.last_persona_switched_at = timezone.now()
        user_settings.updated_by = user
        user_settings.save(update_fields=[
            'active_persona', 'active_role_link', 'active_ig',
            'last_persona_switched_at', 'updated_by', 'updated_at',
        ])

        return CustomResponse(
            general_message="Persona reset to learner.",
            response={"active_persona": "learner"}
        ).get_success_response()


class IGRolesView(APIView):
    """
    GET /api/v1/dashboard/mentor/persona/ig-roles/

    Returns all active IG-scoped Mentor role assignments for the current user.
    Used by the frontend to populate the persona switcher dropdown.
    """
    permission_classes = [CustomizePermission]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        role_links = (
            UserRoleLink.objects
            .select_related('ig', 'role')
            .filter(
                user_id=user_id,
                role__title='Mentor',
                ig__isnull=False,
                is_active=True,
            )
        )

        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()

        serializer = IGRoleItemSerializer(
            role_links,
            many=True,
            context={'mentor_profile': mentor_profile}
        )

        return CustomResponse(
            general_message="IG roles fetched successfully.",
            response={"ig_roles": serializer.data}
        ).get_success_response()
