from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Q

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternTaskStatus
from utils.utils import CommonUtils, DateTimeUtils
from db.intern import InternDailyTimesheet, InternTask
from utils.intern_permissions import ON_LEAVE, current_membership, timesheet_gate, working_membership_error
from db.mentor import SystemActionLog

from .serializers import (
    DUPLICATE_TIMESHEET_CODE,
    InternTimesheetSerializer,
    InternTimesheetHistorySerializer,
    InternTimesheetEditSerializer,
)

# A timesheet stays editable until the end of the second day after its entry_date
# (IST): the Nov 1 timesheet can be submitted on Nov 1 or 2 and edited until Nov 3.
TIMESHEET_EDIT_GRACE_DAYS = 2


def _is_duplicate_timesheet_error(errors) -> bool:
    return any(
        getattr(err, 'code', None) == DUPLICATE_TIMESHEET_CODE
        for err in errors.get('entry_date', [])
    )


def _active_membership_or_error(user_id):
    """
    The intern's current membership if they may submit timesheets, else (None, error
    response): no current row, INACTIVE, before join_date or after end_date (checked
    directly, without waiting for the nightly tenure job).
    """
    link = current_membership(user_id)
    error = working_membership_error(link)
    if error:
        return None, CustomResponse(general_message=error).get_failure_response()
    return link, None


TEAM_SCOPE_PARAM = OpenApiParameter(
    name='scope', required=False, type=str,
    description="current (default): timesheets of the current team stint; previous: older teams "
                "(and earlier stints); all: everything",
)


def _own_timesheets(request, user_id):
    """
    The intern's timesheets for ?scope=current (default), previous or all, plus the
    current membership row (None if they have none). "Current" is the current team
    stint: that team, from its join_date on. Anything else is "previous".
    Returns (queryset, link) or (None, error response) for a bad scope.
    """
    scope = (request.query_params.get('scope') or 'current').lower()
    if scope not in ('current', 'previous', 'all'):
        return None, CustomResponse(general_message="scope must be current, previous or all.").get_failure_response()
    link = current_membership(user_id)
    timesheets = InternDailyTimesheet.objects.select_related('team', 'reviewed_by').filter(user_id=user_id)
    in_current = Q(team_id=link.team_id, entry_date__gte=link.join_date) if link else Q(pk__in=[])
    if scope == 'current':
        timesheets = timesheets.filter(in_current)
    elif scope == 'previous':
        timesheets = timesheets.exclude(in_current)
    return timesheets.order_by('-entry_date'), link


def _duplicate_timesheet_response():
    return CustomResponse(
        general_message="Timesheet for this date already exists."
    ).get_failure_response(status_code=409, http_status_code=409)


class InternTimesheetPrefillAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Retrieve tasks assigned to the intern for the current ISO week. "
            "Used to pre-populate the daily timesheet submission form."
        ),
        responses={200: OpenApiResponse(description="List of this week's tasks for the intern.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        link, error = _active_membership_or_error(user_id)
        if error:
            return error

        if link.intern_status == ON_LEAVE:
            return CustomResponse(response={"tasks": [], "on_leave": True}).get_success_response()

        today = DateTimeUtils.get_ist_today()
        iso_year, iso_week, _ = today.isocalendar()

        tasks = InternTask.objects.filter(
            assigned_to_id=user_id,
            iso_week=iso_week,
            # iso_week alone would also match the same week number of other years.
            deadline__iso_year=iso_year,
            is_archived=False,
        ).filter(
            # Tasks of the current team; tasks from before teams have no team yet.
            Q(team_id=link.team_id) | Q(team__isnull=True)
        ).exclude(
            status='COMPLETED', is_verified=True
        ).order_by('deadline')

        data = [
            {
                "task_id": str(t.id),
                "title": t.title,
                "category": t.category,
                "deadline": t.deadline.isoformat(),
                "status": t.status,
                "complexity": t.complexity,
                "output_link": t.output_link,
                "is_overdue": t.status == 'OVERDUE',
            }
            for t in tasks
        ]

        return CustomResponse(response={"tasks": data, "on_leave": False}).get_success_response()


class InternTimesheetAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "The intern's timesheets (paginated), or one by timesheet_id. `scope`: current (default) "
            "= the current team stint, previous = older teams and earlier stints, all = everything. "
            "Each entry has `team` and `is_current_team`."
        ),
        parameters=[TEAM_SCOPE_PARAM],
        responses={200: InternTimesheetHistorySerializer},
    )
    def get(self, request, timesheet_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if timesheet_id:
            timesheet = InternDailyTimesheet.objects.select_related('team', 'reviewed_by').filter(id=timesheet_id, user_id=user_id).first()
            if not timesheet:
                return CustomResponse(general_message="Timesheet not found.").get_failure_response()
            serializer = InternTimesheetHistorySerializer(timesheet)
            return CustomResponse(response=serializer.data).get_success_response()

        timesheets, link = _own_timesheets(request, user_id)
        if timesheets is None:
            return link  # the error response

        paginated_queryset = CommonUtils.get_paginated_queryset(
            timesheets, request,
            ['entry_date'],
            {'entry_date': 'entry_date'}
        )

        serializer = InternTimesheetHistorySerializer(
            paginated_queryset.get("queryset"), many=True, context={'current_link': link}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Submit a new daily timesheet entry.",
        request=InternTimesheetSerializer,
        responses={200: OpenApiResponse(description="Timesheet submitted successfully.")},
    )
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        link = current_membership(user_id)
        if not link:
            return CustomResponse(general_message="Not an active intern.").get_failure_response()

        if link.intern_status == ON_LEAVE:
            return CustomResponse(general_message="You are currently on approved leave and cannot submit a timesheet.").get_failure_response()

        serializer = InternTimesheetSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            # The day must be inside a tenure; the timesheet belongs to the team that covered it.
            team_id, error = timesheet_gate(link, user_id, serializer.validated_data['entry_date'])
            if error:
                return CustomResponse(general_message=error).get_failure_response()
            serializer.context['team_id'] = team_id
            try:
                serializer.save()
                return CustomResponse(general_message="Timesheet submitted successfully.").get_success_response()
            except IntegrityError:
                # Concurrent submit for the same date hit uq_timesheet_user_date.
                return _duplicate_timesheet_response()
        if _is_duplicate_timesheet_error(serializer.errors):
            return _duplicate_timesheet_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Edit a timesheet entry. Allowed until the end of the second day after its entry_date "
            "(IST): a Nov 1 timesheet can be edited until Nov 3. "
            "edit_reason is mandatory; entry_date cannot be changed."
        ),
        request=InternTimesheetEditSerializer,
        responses={200: OpenApiResponse(description="Timesheet updated successfully.")},
    )
    def patch(self, request, timesheet_id):
        user_id = JWTUtils.fetch_user_id(request)

        # The timesheet keeps the team it was submitted in, even after a move.
        timesheet = InternDailyTimesheet.objects.filter(id=timesheet_id, user_id=user_id).first()
        if not timesheet:
            return CustomResponse(general_message="Timesheet not found.").get_failure_response()

        _, error = timesheet_gate(current_membership(user_id), user_id, timesheet.entry_date)
        if error:
            return CustomResponse(general_message=error).get_failure_response()

        edit_deadline = timesheet.entry_date + timedelta(days=TIMESHEET_EDIT_GRACE_DAYS)
        if DateTimeUtils.get_ist_today() > edit_deadline:
            return CustomResponse(
                general_message="The edit window for this timesheet has closed."
            ).get_failure_response()

        serializer = InternTimesheetEditSerializer(
            instance=timesheet,
            data=request.data,
            partial=True,
            context={'user_id': user_id}
        )
        if not serializer.is_valid():
            return CustomResponse(response=serializer.errors).get_failure_response()

        edit_reason = serializer.validated_data.get("edit_reason")

        old_data = {}
        new_data = {}

        for field, new_val in serializer.validated_data.items():
            if field == 'edit_reason':
                continue

            if field == 'task':
                new_snapshot = [
                    {
                        'task_id': e['task_id'],
                        'title': e.get('title', ''),
                        'status': e['status'],
                        'remark': e.get('remark') or '',
                    }
                    for e in new_val
                ] if new_val is not None else None

                old_val = timesheet.task
                if old_val != new_snapshot:
                    old_data[field] = old_val
                    new_data[field] = new_snapshot
            else:
                old_val = getattr(timesheet, field)
                if old_val != new_val:
                    if field == 'hours':
                        old_data[field] = str(old_val) if old_val else None
                        new_data[field] = str(new_val) if new_val else None
                    else:
                        old_data[field] = old_val
                        new_data[field] = new_val

        if not new_data:
            return CustomResponse(general_message="No editable fields provided or no changes detected.").get_failure_response()

        with transaction.atomic():
            if 'task' in new_data:
                old_task_ids = {t['task_id'] for t in (timesheet.task or [])}
                new_task_ids = {t['task_id'] for t in new_data['task']}
                removed_task_ids = old_task_ids - new_task_ids
                if removed_task_ids:
                    InternTask.objects.filter(id__in=removed_task_ids, assigned_to_id=user_id, is_verified=False).update(status=InternTaskStatus.NOT_STARTED.value)

                for entry in new_data['task']:
                    task_id = entry.get('task_id')
                    new_status = entry.get('status')
                    InternTask.objects.filter(id=task_id, assigned_to_id=user_id).update(status=new_status)

            for field, new_val in new_data.items():
                setattr(timesheet, field, new_val)

            timesheet.edit_reason = edit_reason
            timesheet.save()

            SystemActionLog.objects.create(
                action_type=SystemActionLog.ActionType.INTERN_TIMESHEET_EDIT.value,
                actor_user_id=user_id,
                subject_user_id=user_id,
                entity_name='intern_daily_timesheet',
                entity_id=timesheet.id,
                old_data=old_data,
                new_data=new_data,
                remarks=edit_reason
            )

        return CustomResponse(general_message="Timesheet updated successfully.").get_success_response()


class InternTimesheetTodayAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve today's timesheet entry for the current intern.",
        responses={200: InternTimesheetHistorySerializer},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        today = DateTimeUtils.get_ist_today()

        timesheet = InternDailyTimesheet.objects.select_related('team', 'reviewed_by').filter(user_id=user_id, entry_date=today).first()
        if not timesheet:
            return CustomResponse(general_message="No timesheet submitted for today.").get_failure_response()

        serializer = InternTimesheetHistorySerializer(timesheet)
        return CustomResponse(response=serializer.data).get_success_response()


class InternTimesheetHistoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description=(
            "Paginated timesheet history. `scope`: current (default) = the current team stint, "
            "previous = older teams and earlier stints, all = everything. Each entry has `team` "
            "and `is_current_team`."
        ),
        parameters=[TEAM_SCOPE_PARAM],
        responses={200: InternTimesheetHistorySerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        timesheets, link = _own_timesheets(request, user_id)
        if timesheets is None:
            return link  # the error response

        paginated_queryset = CommonUtils.get_paginated_queryset(
            timesheets, request,
            ['entry_date'],
            {'entry_date': 'entry_date'}
        )

        serializer = InternTimesheetHistorySerializer(
            paginated_queryset.get("queryset"), many=True, context={'current_link': link}
        )
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()
