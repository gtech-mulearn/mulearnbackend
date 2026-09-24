"""
Admin console for "Sign in with muLearn" (plan section 12).

dashboard -> here (role check + audit row) -> authserver internal API (owner of
the data). Four screens, ordered by risk:

  1. Security activity   read-only   recent sign-in attempts
  2. Security posture    read-only   issuer, PKCE, rotation, lifetimes, keys
  3. Sign-in policy      editable    lockout attempts (3-20) and block minutes
  4. Connected apps      editable    register / edit / disable OAuth clients

plus revoking every session of one member.

Never editable from anywhere: the signing key, the issuer, and the PKCE /
rotation / reuse-protection flags. Those are deploy-time settings.

Every change writes a system_action_log row with the before/after snapshot that
authserver returns, so the log records what actually changed.
"""

import logging
from urllib.parse import quote

from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView

from db.mentor import SystemActionLog
from db.user import User
from utils.authserver_client import AuthServerUnavailable, call, error_message
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType

logger = logging.getLogger(__name__)

AUTH_ADMIN_ROLES = [RoleType.ADMIN.value]
Action = SystemActionLog.ActionType
TAGS = ["Dashboard - Auth Admin"]


def _proxy(method, path, *, json=None, params=None):
    """
    Call authserver and translate the result.

    Returns (body, None) on success or (None, failure_response).
    """
    try:
        status, body = call(method, path, json=json, params=params)
    except AuthServerUnavailable as exc:
        return None, CustomResponse(general_message=str(exc)).get_failure_response(
            status_code=503, http_status_code=503
        )
    if status >= 400:
        return None, CustomResponse(
            general_message=error_message(body),
            response={"error": body.get("error"), "fields": body.get("fields")},
        ).get_failure_response(status_code=status, http_status_code=status)
    return body, None


def _incomplete(body, *keys):
    """
    Failure response if a successful change reply lacks the snapshots we need.

    The change has already happened in authserver by this point, so callers
    audit first (with whatever came back) and then return this.
    """
    missing = [k for k in keys if not isinstance(body.get(k), dict)]
    if not missing:
        return None
    logger.error("authserver change reply is missing %s", ", ".join(missing))
    return CustomResponse(
        general_message="The change was sent, but the sign-in service's reply was incomplete. Refresh to check it."
    ).get_failure_response(status_code=502, http_status_code=502)


def _audit(request, action, *, entity_name, entity_id, before=None, after=None, subject_user_id=None, remarks=None):
    """
    Record an admin change. The change has already happened in authserver, so
    a failure here is logged loudly rather than reported as a failed action.
    """
    try:
        SystemActionLog.objects.create(
            action_type=action,
            actor_user_id=JWTUtils.fetch_user_id(request),
            subject_user_id=subject_user_id,
            entity_name=entity_name,
            entity_id=str(entity_id)[:36],
            old_data=before,
            new_data=after,
            remarks=remarks,
        )
    except Exception:
        logger.exception("Could not write system_action_log for %s %s", action, entity_id)


class LoginAttemptsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Recent sign-in attempts. Filters: identifier, result=success|failure, before (ISO time), limit (max 200).")
    @role_required(AUTH_ADMIN_ROLES)
    def get(self, request):
        params = {k: request.query_params.get(k) for k in ("identifier", "result", "before", "limit")
                  if request.query_params.get(k)}
        body, failure = _proxy("GET", "admin/login-attempts/", params=params)
        return failure or CustomResponse(response=body).get_success_response()


class SecurityPostureAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Read-only identity-provider security settings.")
    @role_required(AUTH_ADMIN_ROLES)
    def get(self, request):
        body, failure = _proxy("GET", "admin/security-posture/")
        return failure or CustomResponse(response=body).get_success_response()


class SigninPolicyAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Current sign-in lockout policy and its bounds.")
    @role_required(AUTH_ADMIN_ROLES)
    def get(self, request):
        body, failure = _proxy("GET", "admin/signin-policy/")
        return failure or CustomResponse(response=body).get_success_response()

    @extend_schema(tags=TAGS, description="Update attempts_limit (3-20) and/or block_minutes (1-1440).")
    @role_required(AUTH_ADMIN_ROLES)
    def put(self, request):
        body, failure = _proxy("PUT", "admin/signin-policy/", json=request.data)
        if failure:
            return failure
        _audit(request, Action.AUTH_POLICY_UPDATE, entity_name="system_setting",
               entity_id="auth.lockout", before=body.get("before"), after=body.get("after"))
        if bad := _incomplete(body, "before", "after"):
            return bad
        return CustomResponse(general_message="Sign-in policy updated", response=body["after"]).get_success_response()


class ClientListAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Every registered OAuth client, including disabled ones.")
    @role_required(AUTH_ADMIN_ROLES)
    def get(self, request):
        body, failure = _proxy("GET", "admin/clients/")
        return failure or CustomResponse(response=body).get_success_response()

    @extend_schema(tags=TAGS, description=(
        "Register a client: name, client_id, client_type (public|confidential), redirect_uris, "
        "post_logout_redirect_uris, skip_authorization. A confidential client's secret is "
        "returned ONCE in this response and cannot be recovered."
    ))
    @role_required(AUTH_ADMIN_ROLES)
    def post(self, request):
        body, failure = _proxy("POST", "admin/clients/", json=request.data)
        if failure:
            return failure
        after = body.get("after")
        client_id = after.get("client_id") if isinstance(after, dict) else None
        _audit(request, Action.AUTH_CLIENT_CREATE, entity_name="oauth2_provider_application",
               entity_id=client_id or request.data.get("client_id"), after=after)
        if bad := _incomplete(body, "after"):
            return bad
        return CustomResponse(
            general_message="Client registered",
            response={"client": after, "client_secret": body.get("client_secret")},
        ).get_success_response()


class ClientDetailAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="One OAuth client.")
    @role_required(AUTH_ADMIN_ROLES)
    def get(self, request, client_id):
        body, failure = _proxy("GET", f"admin/clients/{quote(client_id, safe='')}/")
        return failure or CustomResponse(response=body).get_success_response()

    @extend_schema(tags=TAGS, description="Edit name, redirect_uris, post_logout_redirect_uris or skip_authorization. client_id and client_type never change.")
    @role_required(AUTH_ADMIN_ROLES)
    def patch(self, request, client_id):
        body, failure = _proxy("PATCH", f"admin/clients/{quote(client_id, safe='')}/", json=request.data)
        if failure:
            return failure
        _audit(request, Action.AUTH_CLIENT_UPDATE, entity_name="oauth2_provider_application",
               entity_id=client_id, before=body.get("before"), after=body.get("after"))
        if bad := _incomplete(body, "before", "after"):
            return bad
        return CustomResponse(general_message="Client updated", response=body["after"]).get_success_response()


class ClientDisableAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Disable a client and revoke every token it holds. Clients are never deleted.")
    @role_required(AUTH_ADMIN_ROLES)
    def post(self, request, client_id):
        body, failure = _proxy("POST", f"admin/clients/{quote(client_id, safe='')}/disable/")
        if failure:
            return failure
        _audit(request, Action.AUTH_CLIENT_DISABLE, entity_name="oauth2_provider_application",
               entity_id=client_id, before=body.get("before"), after=body.get("after"),
               remarks=request.data.get("reason"))
        if bad := _incomplete(body, "before", "after"):
            return bad
        return CustomResponse(general_message="Client disabled", response=body["after"]).get_success_response()


class ClientEnableAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Re-enable a disabled client. Its old tokens stay revoked.")
    @role_required(AUTH_ADMIN_ROLES)
    def post(self, request, client_id):
        body, failure = _proxy("POST", f"admin/clients/{quote(client_id, safe='')}/enable/")
        if failure:
            return failure
        _audit(request, Action.AUTH_CLIENT_ENABLE, entity_name="oauth2_provider_application",
               entity_id=client_id, before=body.get("before"), after=body.get("after"),
               remarks=request.data.get("reason"))
        if bad := _incomplete(body, "before", "after"):
            return bad
        return CustomResponse(general_message="Client enabled", response=body["after"]).get_success_response()


class SessionRevokeAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=TAGS, description="Sign one member out of every device and app. Body: user_id or muid, optional reason.")
    @role_required(AUTH_ADMIN_ROLES)
    def post(self, request):
        user_id = request.data.get("user_id")
        muid = request.data.get("muid")
        user = None
        if user_id:
            user = User.every.filter(id=user_id).first()
        elif muid:
            user = User.every.filter(muid=muid).first()
        if user is None:
            return CustomResponse(general_message="Member not found").get_failure_response(
                status_code=404, http_status_code=404
            )

        body, failure = _proxy("POST", "sessions/revoke/", json={"user_id": user.id})
        if failure:
            return failure
        complete = body.get("sessions_revoked", False)
        _audit(request, Action.AUTH_SESSION_REVOKE, entity_name="user", entity_id=user.id,
               subject_user_id=user.id, after={"complete": complete},
               remarks=request.data.get("reason"))
        if not complete:
            return CustomResponse(
                general_message="Sessions were only partly revoked. Try again."
            ).get_failure_response(status_code=503, http_status_code=503)
        return CustomResponse(general_message=f"{user.muid} has been signed out everywhere").get_success_response()
