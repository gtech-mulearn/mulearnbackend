"""
Admin-only mentor management views.

Task Request Queue:
    GET    /mentor/admin/task-requests/           — list all pending/all requests (filterable)
    PATCH  /mentor/admin/task-requests/<req_id>/  — approve or reject a request

Tier Management:
    PATCH  /mentor/admin/tier/<mentor_profile_id>/ — change mentor tier
        When tier → VERIFIED: auto-sets is_verified=True, verified_at=now, verified_by=admin
        When tier → NORMAL:   clears is_verified, verified_at, verified_by
"""
import uuid
from django.utils import timezone
from django.db import transaction
from rest_framework.views import APIView

from db.user import User, UserMentor, UserRoleLink
from db.task import TaskList, TaskType
from db.mentor_task_request import MentorTaskRequest
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import CommonUtils
from api.dashboard.mentor.tasks.serializers import MentorTaskRequestSerializer


# ---------------------------------------------------------------------------
# Task request admin queue
# ---------------------------------------------------------------------------

class AdminTaskRequestListView(APIView):
    """
    GET  /mentor/admin/task-requests/
    Lists ALL mentor task creation requests.
    Query params:
        status  — PENDING (default) | APPROVED | REJECTED | ALL
        ig_id   — filter by IG
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        qs = (
            MentorTaskRequest.objects
            .select_related('mentor', 'ig', 'reviewed_by', 'created_task')
            .order_by('-created_at')
        )

        status_filter = request.query_params.get('status', 'PENDING').upper()
        if status_filter != 'ALL':
            if status_filter not in {'PENDING', 'APPROVED', 'REJECTED'}:
                return CustomResponse(
                    general_message="status must be PENDING, APPROVED, REJECTED, or ALL"
                ).get_failure_response()
            qs = qs.filter(status=status_filter)

        ig_id = request.query_params.get('ig_id')
        if ig_id:
            qs = qs.filter(ig_id=ig_id)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=['title', 'hashtag', 'mentor__full_name'],
            sort_fields={'created_at': 'created_at'},
        )
        serializer = MentorTaskRequestSerializer(paginated['queryset'], many=True)
        return CustomResponse(response={
            'data': serializer.data,
            'pagination': paginated['pagination'],
        }).get_success_response()


class AdminTaskRequestActionView(APIView):
    """
    PATCH /mentor/admin/task-requests/<req_id>/

    Approve or reject a mentor's task creation request.

    Body:
        action      : "APPROVE" | "REJECT"  (required)
        admin_note  : string, max 500 chars  (optional)

        # Required only for APPROVE — mirrors TaskList fields not in the request:
        type_id     : UUID of the TaskType   (required for APPROVE)
        level_id    : UUID of the Level      (optional, can be null)
        discord_link: string                 (optional)
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, req_id):
        admin_id = JWTUtils.fetch_user_id(request)
        admin = User.objects.filter(id=admin_id).first()

        req = (
            MentorTaskRequest.objects
            .select_related('mentor', 'ig')
            .filter(id=req_id)
            .first()
        )
        if not req:
            return CustomResponse(
                general_message="Task request not found."
            ).get_failure_response()

        if req.status != MentorTaskRequest.Status.PENDING:
            return CustomResponse(
                general_message=f"This request has already been {req.status.lower()}."
            ).get_failure_response()

        action = str(request.data.get('action', '')).upper()
        if action not in ('APPROVE', 'REJECT'):
            return CustomResponse(
                general_message="action must be 'APPROVE' or 'REJECT'."
            ).get_failure_response()

        admin_note = request.data.get('admin_note', '')
        if admin_note and len(admin_note) > 500:
            return CustomResponse(
                general_message="admin_note must be 500 characters or less."
            ).get_failure_response()

        with transaction.atomic():
            if action == 'APPROVE':
                # Validate type_id
                type_id = request.data.get('type_id')
                if not type_id:
                    return CustomResponse(
                        general_message="type_id is required to approve and create the task."
                    ).get_failure_response()

                task_type = TaskType.objects.filter(id=type_id).first()
                if not task_type:
                    return CustomResponse(
                        general_message="TaskType not found for the given type_id."
                    ).get_failure_response()

                # Prevent duplicate hashtag in TaskList
                if TaskList.objects.filter(hashtag__iexact=req.hashtag).exists():
                    return CustomResponse(
                        general_message=f"A task with hashtag '{req.hashtag}' already exists."
                    ).get_failure_response()

                # Create the actual TaskList entry
                new_task = TaskList.objects.create(
                    id=str(uuid.uuid4()),
                    hashtag=req.hashtag,
                    title=req.title,
                    karma=req.karma,
                    description=req.description,
                    ig=req.ig,
                    type=task_type,
                    level_id=request.data.get('level_id') or None,
                    discord_link=request.data.get('discord_link') or None,
                    active=True,
                    created_by=admin,
                    updated_by=admin,
                )

                req.status = MentorTaskRequest.Status.APPROVED
                req.created_task = new_task
            else:
                req.status = MentorTaskRequest.Status.REJECTED

            req.admin_note   = admin_note or None
            req.reviewed_by  = admin
            req.reviewed_at  = timezone.now()
            req.updated_by   = admin
            req.save()

        serializer = MentorTaskRequestSerializer(req)
        action_word = "approved — task created" if action == 'APPROVE' else "rejected"
        return CustomResponse(
            general_message=f"Task request {action_word}.",
            response=serializer.data,
        ).get_success_response()


# ---------------------------------------------------------------------------
# Mentor tier management
# ---------------------------------------------------------------------------

class AdminMentorTierView(APIView):
    """
    PATCH /mentor/admin/tier/<mentor_profile_id>/

    Change a mentor's tier. mentor_profile_id is the UserMentor.id (PK).

    Body:
        tier            : "NORMAL" | "VERIFIED"  (required)
        verification_note: string, max 500        (optional, used when verifying)

    Side-effects when tier → VERIFIED:
        - UserMentor.is_verified = True
        - UserMentor.verified_at = now()
        - UserMentor.verified_by = admin
        - UserRoleLink.verified  = True  (for all Mentor role links of this user)

    Side-effects when tier → NORMAL:
        - UserMentor.is_verified = False
        - UserMentor.verified_at = None
        - UserMentor.verified_by = None
        - UserRoleLink.verified  unchanged (admin can manually revoke if needed)
    """
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.ADMIN.value])
    def patch(self, request, mentor_profile_id):
        admin_id = JWTUtils.fetch_user_id(request)
        admin = User.objects.filter(id=admin_id).first()

        mentor_profile = (
            UserMentor.objects
            .select_related('user')
            .filter(id=mentor_profile_id)
            .first()
        )
        if not mentor_profile:
            return CustomResponse(
                general_message="Mentor profile not found."
            ).get_failure_response()

        new_tier = str(request.data.get('tier', '')).upper()
        if new_tier not in (UserMentor.MentorTier.NORMAL, UserMentor.MentorTier.VERIFIED):
            return CustomResponse(
                general_message="tier must be 'NORMAL' or 'VERIFIED'."
            ).get_failure_response()

        verification_note = request.data.get('verification_note', '')
        if verification_note and len(verification_note) > 500:
            return CustomResponse(
                general_message="verification_note must be 500 characters or less."
            ).get_failure_response()

        old_tier = mentor_profile.mentor_tier

        with transaction.atomic():
            mentor_profile.mentor_tier  = new_tier
            mentor_profile.updated_by   = admin
            mentor_profile.updated_at   = timezone.now()
            update_fields = ['mentor_tier', 'updated_by_id', 'updated_at']

            if new_tier == UserMentor.MentorTier.VERIFIED:
                mentor_profile.is_verified       = True
                mentor_profile.verified_by       = admin
                mentor_profile.verified_at       = timezone.now()
                mentor_profile.verification_note = verification_note or None
                update_fields += [
                    'is_verified', 'verified_by_id',
                    'verified_at', 'verification_note',
                ]

                # Auto-verify all Mentor UserRoleLinks for this user
                updated = UserRoleLink.objects.filter(
                    user=mentor_profile.user,
                    role__title='Mentor',
                    is_active=True,
                ).update(verified=True)

            elif new_tier == UserMentor.MentorTier.NORMAL and old_tier == UserMentor.MentorTier.VERIFIED:
                # Downgrade — clear verification fields
                mentor_profile.is_verified       = False
                mentor_profile.verified_by       = None
                mentor_profile.verified_at       = None
                mentor_profile.verification_note = None
                update_fields += [
                    'is_verified', 'verified_by_id',
                    'verified_at', 'verification_note',
                ]

            mentor_profile.save(update_fields=update_fields)

        return CustomResponse(
            general_message=f"Mentor tier updated to {new_tier}.",
            response={
                "mentor_profile_id": mentor_profile.id,
                "user_id": mentor_profile.user_id,
                "full_name": mentor_profile.user.full_name,
                "mentor_tier": mentor_profile.mentor_tier,
                "is_verified": mentor_profile.is_verified,
                "verified_at": mentor_profile.verified_at.isoformat() if mentor_profile.verified_at else None,
                "verification_note": mentor_profile.verification_note,
            }
        ).get_success_response()
