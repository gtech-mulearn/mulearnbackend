"""
Mentor-facing task creation request views.

GET  /mentor/tasks/requests/         — list own requests (filtered by status)
POST /mentor/tasks/requests/         — submit a new task creation request
"""
from django.utils import timezone
from rest_framework.views import APIView

from db.mentor_task_request import MentorTaskRequest
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor, _get_persona_context
from utils.response import CustomResponse
from utils.utils import CommonUtils
from .serializers import MentorTaskRequestSerializer


class MentorTaskRequestView(APIView):
    """
    GET  /mentor/tasks/requests/  — list own requests
    POST /mentor/tasks/requests/  — submit new task creation request to admin
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)

        qs = (
            MentorTaskRequest.objects
            .filter(mentor_id=user_id, ig_id=persona_ctx['ig_id'])
            .select_related('ig', 'mentor', 'reviewed_by', 'created_task')
            .order_by('-created_at')
        )

        # Optional status filter
        status_filter = request.query_params.get('status', '').upper()
        if status_filter in {'PENDING', 'APPROVED', 'REJECTED'}:
            qs = qs.filter(status=status_filter)

        paginated = CommonUtils.get_paginated_queryset(
            qs, request,
            search_fields=['title', 'hashtag'],
            sort_fields={'created_at': 'created_at'},
        )

        serializer = MentorTaskRequestSerializer(paginated['queryset'], many=True)
        return CustomResponse(response={
            'data': serializer.data,
            'pagination': paginated['pagination'],
        }).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)
        active_ig_id = persona_ctx.get('ig_id')

        if not active_ig_id:
            return CustomResponse(
                general_message="No active IG persona found."
            ).get_failure_response()

        # Validate required fields
        title   = request.data.get('title', '').strip()
        hashtag = request.data.get('hashtag', '').strip()
        karma   = request.data.get('karma')

        errors = {}
        if not title:
            errors['title'] = 'This field is required.'
        if not hashtag:
            errors['hashtag'] = 'This field is required.'
        if karma is None:
            errors['karma'] = 'This field is required.'
        else:
            try:
                karma = int(karma)
                if karma <= 0:
                    errors['karma'] = 'Karma must be a positive integer.'
            except (TypeError, ValueError):
                errors['karma'] = 'Karma must be a valid integer.'

        if errors:
            return CustomResponse(message=errors).get_failure_response()

        # Prevent duplicate pending requests for the same hashtag in this IG
        duplicate = MentorTaskRequest.objects.filter(
            mentor_id=user_id,
            ig_id=active_ig_id,
            hashtag__iexact=hashtag,
            status='PENDING',
        ).exists()
        if duplicate:
            return CustomResponse(
                general_message=f"A pending request for hashtag '{hashtag}' already exists."
            ).get_failure_response()

        req = MentorTaskRequest.objects.create(
            mentor_id=user_id,
            ig_id=active_ig_id,
            title=title,
            hashtag=hashtag,
            karma=karma,
            description=request.data.get('description', '').strip() or None,
            status=MentorTaskRequest.Status.PENDING,
            created_by_id=user_id,
            updated_by_id=user_id,
        )

        serializer = MentorTaskRequestSerializer(req)
        return CustomResponse(
            general_message="Task creation request submitted. Pending admin review.",
            response=serializer.data,
        ).get_success_response()
