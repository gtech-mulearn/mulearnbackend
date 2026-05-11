"""
Mentor-specific DRF permission classes.

These work in tandem with CustomizePermission (JWT auth).
After auth, views that require IG-scoped mentor access apply one of these classes.

Persona context is read fresh from user_settings on every request —
the DB is the source of truth, not the JWT payload.
"""

from rest_framework.permissions import BasePermission

from db.user import UserRoleLink, UserMentor, UserSettings
from utils.permission import JWTUtils


def _get_persona_context(request):
    """
    Fetch and cache the current user's active persona state from user_settings.
    Attaches result to request._mentor_persona_context to avoid duplicate DB hits
    within the same request cycle.

    Returns a dict with keys: active_persona, role_link_id, ig_id, is_verified
    or None if the user has no active mentor persona.
    """
    if hasattr(request, '_mentor_persona_context'):
        return request._mentor_persona_context

    try:
        user_id = JWTUtils.fetch_user_id(request)
    except Exception:
        request._mentor_persona_context = None
        return None

    settings_qs = (
        UserSettings.objects
        .select_related('active_role_link', 'active_ig')
        .filter(user_id=user_id)
        .first()
    )

    if not settings_qs or settings_qs.active_persona != 'mentor':
        request._mentor_persona_context = None
        return None

    role_link_id = settings_qs.active_role_link_id
    ig_id = settings_qs.active_ig_id

    if not role_link_id or not ig_id:
        request._mentor_persona_context = None
        return None

    # Validate that the role_link is still active (handles mid-session revocation)
    role_link = (
        UserRoleLink.objects
        .filter(id=role_link_id, user_id=user_id, ig_id=ig_id, is_active=True)
        .first()
    )

    if not role_link:
        request._mentor_persona_context = None
        return None

    context = {
        'user_id': user_id,
        'active_persona': 'mentor',
        'role_link_id': role_link_id,
        'ig_id': ig_id,
        'role_link': role_link,
    }
    request._mentor_persona_context = context
    return context


class IsIGMentor(BasePermission):
    """
    Grants access if the user's active persona is 'mentor'
    and the backing user_role_link row is still active.

    Reads from user_settings (DB source of truth).
    Uses request._mentor_persona_context cache — zero extra DB hit if
    another permission class or middleware already populated it.
    """
    message = "Active mentor persona required for this IG."

    def has_permission(self, request, view):
        context = _get_persona_context(request)
        return context is not None


class IsVerifiedIGMentor(BasePermission):
    """
    Extends IsIGMentor: additionally requires is_verified=True and
    mentor_tier='VERIFIED' on the user_mentor row.

    Used for: session creation, boot camp creation, verified-only actions.
    Source of verification: user_mentor table (NOT the role table).
    """
    message = "Verified mentor status required for this action."

    def has_permission(self, request, view):
        context = _get_persona_context(request)
        if not context:
            return False

        return UserMentor.objects.filter(
            user_id=context['user_id'],
            is_verified=True,
            mentor_tier=UserMentor.MentorTier.VERIFIED,
        ).exists()


class HasIGAccess(BasePermission):
    """
    Validates that the IG in the URL kwargs matches the user's active persona IG.
    Prevents cross-IG access even with a valid mentor token.

    Expects URL kwarg named 'ig_id'. Pure in-memory comparison — zero DB hits.
    """
    message = "You do not have mentor access for the requested Interest Group."

    def has_permission(self, request, view):
        context = _get_persona_context(request)
        if not context:
            return False

        url_ig_id = view.kwargs.get('ig_id')
        if not url_ig_id:
            # No IG in URL means not IG-restricted; allow if persona is valid
            return True

        return context['ig_id'] == url_ig_id
