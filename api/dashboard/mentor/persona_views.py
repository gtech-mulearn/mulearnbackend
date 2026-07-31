from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from .serializers import PersonaStatusSerializer, PersonaSwitchSerializer
from db.user import UserSettings, MentorScopeGrant
from db.mentor import SystemActionLog
from db.organization import Organization
from db.task import InterestGroup
from utils.types import RoleType


class PersonaStatusAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Persona"],
        description="""
        Fetches the current user's persona state, including the active persona
        (learner or mentor), the active mentor scope (if any), and a list of all
        available mentor scopes the user can switch to.
        """,
        responses={200: PersonaStatusSerializer}
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user_settings, _ = UserSettings.objects.get_or_create(user_id=user_id)
        
        scope_name = None
        if user_settings.active_persona == 'mentor' and user_settings.active_scope_type:
            scope_type = user_settings.active_scope_type
            scope_id = user_settings.active_scope_id
            
            if scope_type in (MentorScopeGrant.ScopeType.COMPANY_MENTOR.value, MentorScopeGrant.ScopeType.CAMPUS_MENTOR.value):
                org = Organization.objects.filter(id=scope_id).first()
                if org:
                    scope_name = org.title
            elif scope_type == MentorScopeGrant.ScopeType.IG_MENTOR.value:
                ig = InterestGroup.objects.filter(id=scope_id).first()
                if ig:
                    scope_name = ig.name
            elif scope_type == MentorScopeGrant.ScopeType.MENTOR.value:
                scope_name = "Global Mentor"

        data = {
            "active_persona": user_settings.active_persona or 'learner',
            "active_scope_type": user_settings.active_scope_type,
            "active_scope_id": user_settings.active_scope_id,
            "active_scope_name": scope_name
        }
        serializer = PersonaStatusSerializer(data)
        return CustomResponse(response=serializer.data).get_success_response()


class PersonaSwitchAPI(APIView):
    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Persona"],
        description="Allows a mentor to switch between 'learner' and 'mentor' personas, or between different mentor scopes.",
        request=PersonaSwitchSerializer,
        responses={200: PersonaStatusSerializer}
    )
    @role_required([RoleType.MENTOR.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        serializer = PersonaSwitchSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(message=serializer.errors).get_failure_response()

        validated_data = serializer.validated_data
        persona = validated_data.get("persona")

        user_settings, _ = UserSettings.objects.get_or_create(user_id=user_id)
        old_persona_data = {
            "persona": user_settings.active_persona,
            "scope_type": user_settings.active_scope_type,
            "scope_id": user_settings.active_scope_id,
        }

        if persona == "learner":
            user_settings.active_persona = "learner"
            user_settings.active_scope_type = None
            user_settings.active_scope_id = None
        elif persona == "mentor":
            # A deactivated mentor cannot switch to a mentor persona.
            from db.user import UserMentor
            mentor_profile = UserMentor.objects.filter(user_id=user_id).first()
            if mentor_profile and not mentor_profile.is_active:
                return CustomResponse(
                    general_message="Your mentor account is deactivated. You cannot switch to a mentor persona."
                ).get_failure_response(status_code=403)

            # Determine the single active scope from the latest grant
            latest_grant = MentorScopeGrant.objects.filter(
                application__user_id=user_id,
                is_active=True
            ).order_by('-granted_at').first()
            
            if not latest_grant:
                return CustomResponse(
                    general_message="You do not have an active mentor role to switch to."
                ).get_failure_response(status_code=403)

            user_settings.active_persona = "mentor"
            user_settings.active_scope_type = latest_grant.scope_type
            user_settings.active_scope_id = latest_grant.scope_id

        user_settings.save()

        # Use the GET view's logic to return the new state
        return PersonaStatusAPI().get(request)