from rest_framework.views import APIView

from db.user import User, UserRoleLink, UserMentor, UserSettings
from db.task import InterestGroup
from db.mentor import MentorshipSession, MentorshipSessionUserLink
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor, _get_persona_context
from utils.response import CustomResponse


class MentorOverviewView(APIView):
    """
    GET /api/v1/dashboard/mentor/overview/

    Returns a full dashboard snapshot for the active mentor persona:
    - User details
    - Mentor profile (with tier + verification)
    - Active persona context (IG, role_link)
    - All authorized IGs (not just the active one)
    - Key stats (mentees, sessions, pending approvals, hours)
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        # persona_context already validated and cached by IsIGMentor
        persona_ctx = _get_persona_context(request)

        user = User.objects.filter(id=user_id).first()
        mentor_profile = UserMentor.objects.filter(user_id=user_id).first()

        # All active IG-scoped mentor role links for this user
        ig_role_links = (
            UserRoleLink.objects
            .select_related('ig')
            .filter(user_id=user_id, role__title='Mentor', ig__isnull=False, is_active=True)
        )

        authorized_igs = [
            {
                "role_link_id": str(rl.id),
                "ig_id": str(rl.ig.id),
                "ig_name": rl.ig.name,
                "is_primary": rl.is_primary,
                "is_verified": mentor_profile.is_verified if mentor_profile else False,
            }
            for rl in ig_role_links
        ]

        active_ig_id = persona_ctx['ig_id']

        # Stats scoped to current active IG
        total_mentees = (
            MentorshipSessionUserLink.objects
            .filter(
                session__ig_id=active_ig_id,
                participant_role='MENTEE',
            )
            .values('user_id').distinct().count()
        )

        sessions_conducted = (
            MentorshipSessionUserLink.objects
            .filter(
                user_id=user_id,
                participant_role='MENTOR',
                session__ig_id=active_ig_id,
                session__status='COMPLETED',
            )
            .count()
        )

        # mentor_review_status is a planned column not yet added to KarmaActivityLog.
        # Returns 0 safely until the ALTER TABLE migration is executed.
        pending_approvals = 0

        return CustomResponse(
            general_message="Mentor overview fetched.",
            response={
                "user": {
                    "full_name": user.full_name,
                    "muid": user.muid,
                    "profile_pic": user.profile_pic,
                },
                "mentor_profile": {
                    "about": mentor_profile.about if mentor_profile else None,
                    "expertise": mentor_profile.expertise if mentor_profile else None,
                    "reason": mentor_profile.reason if mentor_profile else None,
                    "volunteer_hours": mentor_profile.hours if mentor_profile else 0,
                    "mentor_tier": mentor_profile.mentor_tier if mentor_profile else "NORMAL",
                    "is_verified": mentor_profile.is_verified if mentor_profile else False,
                },
                "active_persona": {
                    "active_persona": "mentor",
                    "active_role_link_id": persona_ctx['role_link_id'],
                    "active_ig_id": active_ig_id,
                    "ig_name": persona_ctx['role_link'].ig.name if persona_ctx['role_link'].ig else None,
                    "is_verified": mentor_profile.is_verified if mentor_profile else False,
                },
                "authorized_igs": authorized_igs,
                "stats": {
                    "total_mentees": total_mentees,
                    "sessions_conducted": sessions_conducted,
                    "pending_task_approvals": pending_approvals,
                    "volunteer_hours": mentor_profile.hours if mentor_profile else 0,
                },
            }
        ).get_success_response()
