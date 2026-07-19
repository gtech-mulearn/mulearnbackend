"""
Event Task Management API views.
CRUD operations for tasks linked to events.
Event organiser / co-owner / admin access required.
"""
import uuid

from rest_framework.views import APIView

from db.events import Event
from db.task import TaskList, TaskType, Channel, InterestGroup, Level
from db.organization import Organization
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.utils import CommonUtils, DateTimeUtils
from utils.types import RoleType

from .serializers import (
    EventTaskSerializer,
    EventTaskWriteSerializer,
    can_manage_event,
    get_live_events,
)
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


def _check_event_task_permission(request, event_id):
    """
    Validate that the event exists and the caller can manage it.
    Returns (event, user_id, error_response) — error_response is None on success.
    """
    user_id = JWTUtils.fetch_user_id(request)
    roles = JWTUtils.fetch_role(request)

    event = get_live_events().filter(id=event_id).first()
    if not event:
        return None, user_id, CustomResponse(
            general_message='Event not found.'
        ).get_failure_response()

    is_admin = RoleType.ADMIN.value in roles
    if not is_admin and not can_manage_event(user_id, event):
        return None, user_id, CustomResponse(
            general_message='You do not have permission to manage tasks for this event.'
        ).get_failure_response()

    return event, user_id, None


# ─────────────────────────────────────────────────────────────────────────────
# EVENT TASK LIST + CREATE
# ─────────────────────────────────────────────────────────────────────────────

class EventTaskListCreateAPI(APIView):
    """
    GET  /events/manage/<event_id>/tasks/   → list tasks linked to this event
    POST /events/manage/<event_id>/tasks/   → create a new task linked to this event
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="List all tasks linked to an event.",
        responses={200: EventTaskSerializer(many=True)},
    )
    def get(self, request, event_id):
        event, user_id, error = _check_event_task_permission(request, event_id)
        if error:
            return error

        tasks = TaskList.objects.select_related(
            'type', 'ig', 'level', 'channel', 'org', 'created_by'
        ).filter(event_fk=event)

        paginated = CommonUtils.get_paginated_queryset(
            tasks,
            request,
            search_fields=['title', 'hashtag', 'description'],
            sort_fields={
                'created_at': 'created_at',
                'karma': 'karma',
                'title': 'title',
            },
        )

        serializer = EventTaskSerializer(
            paginated.get('queryset'), many=True
        )

        return CustomResponse().paginated_response(
            data=serializer.data,
            pagination=paginated.get('pagination'),
        )

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Create a new task linked to an event. Task will require admin approval.",
        request=EventTaskWriteSerializer,
        responses={200: EventTaskSerializer},
    )
    def post(self, request, event_id):
        event, user_id, error = _check_event_task_permission(request, event_id)
        if error:
            return error

        serializer = EventTaskWriteSerializer(data=request.data)
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        now = DateTimeUtils.get_current_utc_time()
        task = serializer.save(
            id=uuid.uuid4(),
            event_fk=event,
            approval_status='pending',
            active=False,
            variable_karma=False,
            usage_count=1,
            created_by_id=user_id,
            updated_by_id=user_id,
            created_at=now,
            updated_at=now,
        )

        # Re-fetch with select_related for the response
        task = TaskList.objects.select_related(
            'type', 'ig', 'level', 'channel', 'org', 'created_by'
        ).get(pk=task.pk)

        return CustomResponse(
            general_message='Task created and linked to event. Pending admin approval.',
            response=EventTaskSerializer(task).data,
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# EVENT TASK DETAIL (GET / PATCH / DELETE)
# ─────────────────────────────────────────────────────────────────────────────

class EventTaskDetailAPI(APIView):
    """
    GET    /events/manage/<event_id>/tasks/<task_id>/   → task detail
    PATCH  /events/manage/<event_id>/tasks/<task_id>/   → partial update
    DELETE /events/manage/<event_id>/tasks/<task_id>/   → delete task
    """
    authentication_classes = [CustomizePermission]

    def _get_task(self, event, task_id):
        """Get a task that belongs to the given event."""
        return TaskList.objects.select_related(
            'type', 'ig', 'level', 'channel', 'org', 'created_by'
        ).filter(id=task_id, event_fk=event).first()

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve a specific task linked to an event.",
        responses={200: EventTaskSerializer},
    )
    def get(self, request, event_id, task_id):
        event, user_id, error = _check_event_task_permission(request, event_id)
        if error:
            return error

        task = self._get_task(event, task_id)
        if not task:
            return CustomResponse(
                general_message='Task not found or does not belong to this event.'
            ).get_failure_response()

        return CustomResponse(
            general_message='Task detail retrieved.',
            response=EventTaskSerializer(task).data,
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Partially update a task linked to an event.",
        request=EventTaskWriteSerializer,
        responses={200: EventTaskSerializer},
    )
    def patch(self, request, event_id, task_id):
        event, user_id, error = _check_event_task_permission(request, event_id)
        if error:
            return error

        task = self._get_task(event, task_id)
        if not task:
            return CustomResponse(
                general_message='Task not found or does not belong to this event.'
            ).get_failure_response()

        serializer = EventTaskWriteSerializer(task, data=request.data, partial=True)
        if not serializer.is_valid():
            return CustomResponse(
                message=serializer.errors
            ).get_failure_response()

        serializer.save(
            updated_by_id=user_id,
            updated_at=DateTimeUtils.get_current_utc_time(),
        )

        # Re-fetch with select_related for the response
        task = TaskList.objects.select_related(
            'type', 'ig', 'level', 'channel', 'org', 'created_by'
        ).get(pk=task_id)

        return CustomResponse(
            general_message='Task updated successfully.',
            response=EventTaskSerializer(task).data,
        ).get_success_response()

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Delete a task linked to an event.",
        responses={200: inline_serializer(
            name='EventTaskDeleteResponse',
            fields={'message': s.CharField()},
        )},
    )
    def delete(self, request, event_id, task_id):
        event, user_id, error = _check_event_task_permission(request, event_id)
        if error:
            return error

        task = self._get_task(event, task_id)
        if not task:
            return CustomResponse(
                general_message='Task not found or does not belong to this event.'
            ).get_failure_response()

        task.delete()

        return CustomResponse(
            general_message='Task deleted successfully.',
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# EVENT TASK METADATA (dropdown data)
# ─────────────────────────────────────────────────────────────────────────────

class EventTaskMetaAPI(APIView):
    """
    GET /events/manage/<event_id>/tasks/meta/
    Returns dropdown data for task creation/editing forms.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve dropdown metadata for event task forms.",
        responses={200: inline_serializer(
            name='EventTaskMetaResponse',
            fields={
                'task_types': s.ListField(child=s.DictField()),
                'interest_groups': s.ListField(child=s.DictField()),
                'levels': s.ListField(child=s.DictField()),
                'channels': s.ListField(child=s.DictField()),
                'organizations': s.ListField(child=s.DictField()),
            },
        )},
    )
    def get(self, request, event_id):
        event, user_id, error = _check_event_task_permission(request, event_id)
        if error:
            return error

        return CustomResponse(
            general_message='Task metadata retrieved.',
            response={
                'task_types': list(
                    TaskType.objects.values('id', 'title').order_by('title')
                ),
                'interest_groups': list(
                    InterestGroup.objects.values('id', 'name').order_by('name')
                ),
                'levels': list(
                    Level.objects.values('id', 'name').order_by('name')
                ),
                'channels': list(
                    Channel.objects.values('id', 'name').order_by('name')
                ),
                'organizations': list(
                    Organization.objects.values('id', 'title').order_by('title')
                ),
            },
        ).get_success_response()
