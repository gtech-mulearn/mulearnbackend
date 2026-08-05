"""
Mentor-specific DRF permission classes.

These work in tandem with CustomizePermission (JWT auth).
After auth, views that require active-mentor-persona access apply one of
these classes.

Persona context is read fresh from user_settings on every request —
the DB is the source of truth, not the JWT payload. Tier membership is
validated against MentorScopeGrant, not any field on UserMentor (which
carries no tier/status of its own — see db/user.py).

Not retrofitted onto every existing `role_required([MENTOR])` view — that
would be a bigger behavioral change than needed. New endpoints that want a
persona-scoped check should use these explicitly.
"""

from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from db.user import UserSettings, MentorScopeGrant
from utils.permission import JWTUtils


def _get_persona_context(request):
    """
    Fetch and cache the current user's active persona state from user_settings.
    Attaches result to request._mentor_persona_context to avoid duplicate DB hits
    within the same request cycle.

    Returns a dict with keys: user_id, active_persona, scope_type, scope_id
    or None if the user has no active mentor persona backed by a real grant.
    """
    if hasattr(request, '_mentor_persona_context'):
        return request._mentor_persona_context

    try:
        user_id = JWTUtils.fetch_user_id(request)
    except Exception:
        request._mentor_persona_context = None
        return None

    settings_row = UserSettings.objects.filter(user_id=user_id).first()

    if not settings_row or settings_row.active_persona != 'mentor':
        request._mentor_persona_context = None
        return None

    scope_type = settings_row.active_scope_type
    scope_id = settings_row.active_scope_id

    if not scope_type:
        request._mentor_persona_context = None
        return None

    # Validate the active scope is still backed by a real, active grant
    # (handles mid-session revocation).
    grant = MentorScopeGrant.objects.filter(
        mentor__user_id=user_id,
        mentor__is_active=True,
        scope_type=scope_type,
        scope_id=scope_id,
        is_active=True,
    ).first()

    if not grant:
        request._mentor_persona_context = None
        return None

    context = {
        'user_id': user_id,
        'active_persona': 'mentor',
        'scope_type': scope_type,
        'scope_id': scope_id,
        'grant': grant,
    }
    request._mentor_persona_context = context
    return context


class HasActiveMentorPersona(BasePermission):
    """
    Grants access if the user's active persona is 'mentor' and the backing
    scope is still covered by an active MentorScopeGrant.

    Reads from user_settings (DB source of truth).
    Uses request._mentor_persona_context cache — zero extra DB hit if
    another permission class or middleware already populated it.
    """
    message = "Active mentor persona required for this action."

    def has_permission(self, request, view):
        context = _get_persona_context(request)
        if context is None:
            raise PermissionDenied(self.message)
        return True


class HasActiveScopeAccess(BasePermission):
    """
    Validates that the scope in the URL kwargs matches the user's active
    persona scope. Prevents cross-scope access even with a valid mentor
    token. Tier-agnostic — works for IG/company/campus scopes alike.

    Expects a URL kwarg named 'ig_id', 'org_id', or 'scope_id' (checked in
    that order). Pure in-memory comparison beyond the initial context fetch.
    """
    message = "You do not have mentor access for the requested scope."

    def has_permission(self, request, view):
        context = _get_persona_context(request)
        if not context:
            raise PermissionDenied(self.message)

        url_scope_id = (
            view.kwargs.get('ig_id')
            or view.kwargs.get('org_id')
            or view.kwargs.get('scope_id')
        )
        if not url_scope_id:
            # No scope in URL means not scope-restricted; allow if persona is valid
            return True

        if str(context['scope_id']) != str(url_scope_id):
            raise PermissionDenied(self.message)

        return True
