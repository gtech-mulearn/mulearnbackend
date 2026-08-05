from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from utils.permission import CustomizePermission, JWTUtils, role_required, mentor_active_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from db.mentor import MentorshipSession
from . import serializers


class StudentSessionRequestAPI(APIView):
    """
    POST /session/student/request/

    Allows any authenticated user (students, learners, etc.) to request a
    mentorship session from the mentor(s) assigned to their entity.

    The request is created with status=REQUESTED and the student is
    automatically added as an invited MENTEE. The `requested_by` field
    permanently records the originating student even after the mentor
    adopts the session.

    Validation enforced:
      - Student must be a verified member of the target entity.
      - `starts_at` must be in the future and before `ends_at`.
      - Mode / venue / meeting-link rules (same as session create).
      - No duplicate REQUESTED session (same student + entity + title + starts_at).
    """

    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Student Session Request"],
        description=(
            "Request a mentorship session from the mentor(s) of a campus, company, or IG. "
            "The student must be a verified member of the target entity. "
            "The session starts in REQUESTED status and waits for a mentor to approve or reject it."
        ),
        request=serializers.StudentSessionRequestSerializer,
        responses={201: serializers.StudentSessionRequestSerializer},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        serializer = serializers.StudentSessionRequestSerializer(
            data=request.data,
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            session = serializer.save()
            return CustomResponse(
                general_message="Session request submitted successfully. "
                                "A mentor will review your request shortly.",
                response=serializers.StudentSessionRequestSerializer(session).data,
            ).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


class StudentSessionRequestListAPI(APIView):
    """
    GET /session/student/my-requests/

    Returns the logged-in student's own session requests, optionally filtered
    by status (REQUESTED / APPROVED / REJECTED).
    """

    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Student Session Request"],
        description="List all session requests made by the logged-in student.",
        parameters=[
            OpenApiParameter(
                "status", OpenApiTypes.STR, OpenApiParameter.QUERY, required=False,
                description="Filter by status: REQUESTED, PENDING_APPROVAL, REJECTED, etc."
            ),
        ],
        responses={200: serializers.StudentSessionRequestListSerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)

        sessions = MentorshipSession.objects.filter(
            requested_by_id=user_id,
            is_deleted=False,
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            sessions = sessions.filter(status=status_filter)

        paginated_queryset = CommonUtils.get_paginated_queryset(
            sessions, request,
            search_fields=["title", "description"],
            sort_fields={"created_at": "created_at", "starts_at": "starts_at"},
        )

        serializer = serializers.StudentSessionRequestListSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class MentorStudentRequestListAPI(APIView):
    """
    GET /session/student-requests/

    Returns all REQUESTED sessions that fall within the logged-in mentor's
    scope. All sessions are Interest-Group scoped, so a mentor sees requests
    for the IGs they actively mentor — regardless of mentor tier.

    Scoping rules:
      - Global MENTOR → All REQUESTED sessions (admin-level visibility).
      - Any other tier (IG / COMPANY / CAMPUS mentor) → IG_SESSION requests
        whose entity_id is one of the mentor's active MENTOR Interest Groups.
        (A company/campus mentor who also mentors IGs sees those IG requests.)
    """

    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Session Request"],
        description=(
            "List all pending student session requests that are within the logged-in "
            "mentor's scope (their assigned IGs, campus, or company)."
        ),
        responses={200: serializers.StudentSessionRequestListSerializer(many=True)},
    )
    @role_required([RoleType.MENTOR.value])
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        from db.task import UserIgLink
        from db.user import MentorScopeGrant
        from api.dashboard.mentor.dash_mentor_helper import get_mentor_scopes

        # Active scopes for this user (grant-driven, falls back to
        # mentor_tier for accounts that predate grants).
        scopes = get_mentor_scopes(user_id)

        if not scopes:
            # Has the MENTOR role but no approved record → no visibility.
            sessions = MentorshipSession.objects.none()
        elif (MentorScopeGrant.ScopeType.MENTOR, None) in scopes:
            # Global mentor: admin-level visibility into all pending requests.
            sessions = MentorshipSession.objects.filter(
                status=MentorshipSession.Status.REQUESTED,
                is_deleted=False,
            )
        else:
            # Any other tier mentors Interest Groups via active MENTOR links.
            # All sessions are IG-scoped, so they see IG_SESSION requests for
            # the IGs they actively mentor — independent of tier.
            ig_ids = list(
                UserIgLink.objects.filter(
                    user_id=user_id,
                    assignment_type=UserIgLink.AssignmentType.MENTOR,
                    is_active=True,
                ).values_list("ig_id", flat=True)
            )
            if not ig_ids:
                sessions = MentorshipSession.objects.none()
            else:
                sessions = MentorshipSession.objects.filter(
                    session_type=MentorshipSession.SessionType.IG_SESSION,
                    entity_id__in=ig_ids,
                    status=MentorshipSession.Status.REQUESTED,
                    is_deleted=False,
                )

        paginated_queryset = CommonUtils.get_paginated_queryset(
            sessions, request,
            search_fields=["title", "requested_by__full_name"],
            sort_fields={"created_at": "created_at", "starts_at": "starts_at"},
        )

        serializer = serializers.StudentSessionRequestListSerializer(
            paginated_queryset.get("queryset"), many=True
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination"),
            }
        ).get_success_response()


class MentorStudentRequestVerifyAPI(APIView):
    """
    PATCH /session/student-requests/<session_id>/verify/

    Allows a mentor to approve or reject a student's session request.

    The mentor must be eligible to act on the session (their scope must
    include the session's entity_id + session_type).

    On APPROVE:
      - The session moves from REQUESTED → SCHEDULED directly (mentor
        approval is the trust gate — there is no separate admin step).
      - `created_by` is updated to this mentor (so it appears in their dashboard).
      - `requested_by` is preserved for audit purposes.
      - Optional field overrides (starts_at, ends_at, mode, meeting_link, venue)
        allow the mentor to adjust the proposed logistics before approving.

    On REJECT:
      - The session moves from REQUESTED → REJECTED.
      - The student can query their own requests to see the rejection.
    """

    permission_classes = [CustomizePermission]

    @extend_schema(
        tags=["Dashboard - Mentor Session Request"],
        description=(
            "Approve or reject a student's session request. "
            "Only mentors whose scope covers the session's entity may act on it. "
            "When approving, optional overrides for starts_at, ends_at, mode, "
            "meeting_link, and venue allow the mentor to adjust logistics."
        ),
        request=serializers.MentorStudentRequestVerifySerializer,
    )
    @role_required([RoleType.MENTOR.value])
    @mentor_active_required
    def patch(self, request, session_id):
        user_id = JWTUtils.fetch_user_id(request)

        # Fetch the session — must be in REQUESTED state and not deleted
        session = MentorshipSession.objects.filter(
            id=session_id,
            status=MentorshipSession.Status.REQUESTED,
            is_deleted=False,
        ).first()

        if not session:
            return CustomResponse(
                general_message="Session request not found or is not in REQUESTED status."
            ).get_failure_response(status_code=404)

        # ── Scope check: verify this mentor is eligible to act on this session ──
        if not _mentor_can_act(user_id, session):
            return CustomResponse(
                general_message="You do not have permission to act on this session request."
            ).get_failure_response(status_code=403)

        serializer = serializers.MentorStudentRequestVerifySerializer(
            session,
            data=request.data,
            context={"user_id": user_id},
        )
        if serializer.is_valid():
            serializer.save()
            action = serializer.validated_data["status"]
            if action == "APPROVED":
                msg = (
                    "Session request approved and scheduled. "
                    "You can manage it from your sessions dashboard."
                )
            else:
                msg = "Session request rejected."

            return CustomResponse(general_message=msg).get_success_response()

        return CustomResponse(message=serializer.errors).get_failure_response()


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _mentor_can_act(user_id: str, session: MentorshipSession) -> bool:
    """
    Returns True if the given user (mentor) is authorised to approve/reject
    the session. All sessions are Interest-Group scoped, so eligibility is:

      - Global MENTOR → may act on anything.
      - Any other tier → may act on an IG_SESSION request for an Interest Group
        they actively mentor (i.e., they have an active IG_MENTOR grant for it).
    """
    from db.user import MentorScopeGrant
    from api.dashboard.mentor.dash_mentor_helper import has_scope

    # Global mentor can act on anything.
    if has_scope(user_id, MentorScopeGrant.ScopeType.MENTOR):
        return True

    if session.session_type != MentorshipSession.SessionType.IG_SESSION:
        return False

    # Check for a specific IG_MENTOR grant for this session's IG.
    return has_scope(
        user_id,
        MentorScopeGrant.ScopeType.IG_MENTOR,
        session.entity_id
    )
