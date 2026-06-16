from django.db import IntegrityError
from django.utils.timezone import now

from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType, InternGuildStatus
from utils.utils import CommonUtils
from db.intern import InternDailyTimesheet, UserInternGuildLink, InternTask
from db.achievement import UserStreak

from .serializers import InternTimesheetSerializer, InternTimesheetHistorySerializer


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
        description="Edit end-of-day note on a timesheet entry.",
        responses={200: OpenApiResponse(description="Timesheet updated successfully.")},
    )
    def patch(self, request, timesheet_id):
        user_id = JWTUtils.fetch_user_id(request)

        timesheet = InternDailyTimesheet.objects.filter(id=timesheet_id, user_id=user_id).first()
        if not timesheet:
            return CustomResponse(general_message="Timesheet not found.").get_failure_response()

        if timesheet.status == 'APPROVED':
            return CustomResponse(general_message="Cannot edit an approved timesheet.").get_failure_response()

        edit_reason = request.data.get("edit_reason")
        if not edit_reason:
            return CustomResponse(general_message="edit_reason is mandatory for modifications.").get_failure_response()

        allowed_fields = ["end_of_day_note"]
        old_data = {}
        new_data = {}

        for field in allowed_fields:
            if field in request.data:
                old_val = getattr(timesheet, field)
                new_val = request.data[field]
                if old_val != new_val:
                    old_data[field] = old_val
                    new_data[field] = new_val
                    setattr(timesheet, field, new_val)

        if not new_data:
            return CustomResponse(general_message="No editable fields provided or no changes detected.").get_failure_response()

        timesheet.edit_reason = edit_reason
        timesheet.save()

        from db.mentor import SystemActionLog
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
