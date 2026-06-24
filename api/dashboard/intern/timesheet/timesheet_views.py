from django.db import IntegrityError, transaction
from django.utils.timezone import now

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternGuildStatus, InternTaskStatus
from utils.utils import CommonUtils
from db.intern import InternDailyTimesheet, UserInternGuildLink, InternTask
from db.achievement import UserStreak
from db.mentor import SystemActionLog

from .serializers import InternTimesheetSerializer, InternTimesheetHistorySerializer, InternTimesheetEditSerializer


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
        guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()

        if not guild_link or guild_link.status == InternGuildStatus.INACTIVE.value:
            return CustomResponse(general_message="Not an active intern.").get_failure_response()

        if guild_link.status == InternGuildStatus.ON_LEAVE.value:
            return CustomResponse(response={"tasks": [], "on_leave": True}).get_success_response()

        today = now().date()
        _, iso_week, _ = today.isocalendar()

        tasks = InternTask.objects.filter(
            assigned_to_id=user_id,
            iso_week=iso_week,
            is_archived=False,
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
        description="Retrieve intern timesheet(s). Pass a timesheet_id to retrieve a specific entry.",
        responses={200: InternTimesheetHistorySerializer},
    )
    def get(self, request, timesheet_id=None):
        user_id = JWTUtils.fetch_user_id(request)
        if timesheet_id:
            timesheet = InternDailyTimesheet.objects.filter(id=timesheet_id, user_id=user_id).first()
            if not timesheet:
                return CustomResponse(general_message="Timesheet not found.").get_failure_response()
            serializer = InternTimesheetHistorySerializer(timesheet)
            return CustomResponse(response=serializer.data).get_success_response()

        timesheets = InternDailyTimesheet.objects.filter(user_id=user_id).order_by('-entry_date')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            timesheets, request,
            ['entry_date', 'status'],
            {'entry_date': 'entry_date', 'status': 'status'}
        )

        serializer = InternTimesheetHistorySerializer(paginated_queryset.get("queryset"), many=True)
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
        guild_link = UserInternGuildLink.objects.filter(user_id=user_id).first()

        if not guild_link or guild_link.status == InternGuildStatus.INACTIVE.value:
            return CustomResponse(general_message="Not an active intern.").get_failure_response()

        if guild_link.status == InternGuildStatus.ON_LEAVE.value:
            return CustomResponse(general_message="You are currently on approved leave and cannot submit a timesheet.").get_failure_response()

        serializer = InternTimesheetSerializer(data=request.data, context={'user_id': user_id})
        if serializer.is_valid():
            try:
                serializer.save()
                return CustomResponse(general_message="Timesheet submitted successfully.").get_success_response()
            except IntegrityError:
                return CustomResponse(general_message="Timesheet for this date already exists.", status_code=409).get_failure_response()
        return CustomResponse(response=serializer.errors).get_failure_response()

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Edit fields on a pending timesheet entry.",
        request=InternTimesheetEditSerializer,
        responses={200: OpenApiResponse(description="Timesheet updated successfully.")},
    )
    def patch(self, request, timesheet_id):
        user_id = JWTUtils.fetch_user_id(request)

        timesheet = InternDailyTimesheet.objects.filter(id=timesheet_id, user_id=user_id).first()
        if not timesheet:
            return CustomResponse(general_message="Timesheet not found.").get_failure_response()

        if timesheet.status != 'PENDING':
            return CustomResponse(general_message="Only works on timesheets with status = PENDING.").get_failure_response()

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
                    if field == 'entry_date':
                        old_data[field] = str(old_val) if old_val else None
                        new_data[field] = str(new_val) if new_val else None
                    elif field == 'hours':
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
        today = now().date()

        timesheet = InternDailyTimesheet.objects.filter(user_id=user_id, entry_date=today).first()
        if not timesheet:
            return CustomResponse(general_message="No timesheet submitted for today.").get_failure_response()

        serializer = InternTimesheetHistorySerializer(timesheet)
        return CustomResponse(response=serializer.data).get_success_response()


class InternTimesheetHistoryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve paginated intern timesheet history.",
        responses={200: InternTimesheetHistorySerializer(many=True)},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        timesheets = InternDailyTimesheet.objects.filter(user_id=user_id).order_by('-entry_date')

        paginated_queryset = CommonUtils.get_paginated_queryset(
            timesheets, request,
            ['entry_date', 'status'],
            {'entry_date': 'entry_date', 'status': 'status'}
        )

        serializer = InternTimesheetHistorySerializer(paginated_queryset.get("queryset"), many=True)
        return CustomResponse(
            response={
                "data": serializer.data,
                "pagination": paginated_queryset.get("pagination")
            }
        ).get_success_response()


class InternTimesheetSummaryAPI(APIView):
    authentication_classes = [CustomizePermission]

    @role_required([RoleType.INTERN.value])
    @extend_schema(
        tags=['Dashboard - Intern'],
        description="Retrieve current timesheet streak stats (current and longest streak).",
        responses={200: OpenApiResponse(description="Streak stats for the intern.")},
    )
    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        streak = UserStreak.objects.filter(user_id=user_id, streak_type='intern_timesheet').first()

        data = {
            "current_streak": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
        }
        return CustomResponse(response=data).get_success_response()
