"""
Event Analytics API views.
Provides performance stats for event organisers.
"""
from rest_framework.views import APIView

from django.db.models import Sum, Count
from django.db.models.functions import TruncDate

from db.events import EventInterest, EventConnection
from db.task import TaskList, KarmaActivityLog
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
from utils.types import RoleType

from .serializers import can_manage_event, get_live_events
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


class EventAnalyticsAPI(APIView):
    """
    GET /events/manage/<event_id>/analytics/
    Returns performance stats for the event:
      - summary (interests, tasks, completions, karma)
      - interest_trend (day-by-day)
      - task_breakdown (per-task completions + karma)
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Dashboard - Events'],
        description="Retrieve analytics and performance stats for an event.",
        responses={200: inline_serializer(
            name='EventAnalyticsResponse',
            fields={
                'summary': s.DictField(),
                'interest_trend': s.ListField(child=s.DictField()),
                'task_breakdown': s.ListField(child=s.DictField()),
            },
        )},
    )
    def get(self, request, event_id):
        user_id = JWTUtils.fetch_user_id(request)
        roles = JWTUtils.fetch_role(request)

        event = get_live_events().filter(id=event_id).first()
        if not event:
            return CustomResponse(
                general_message='Event not found.'
            ).get_failure_response()

        is_admin = RoleType.ADMIN.value in roles
        if not is_admin and not can_manage_event(user_id, event):
            return CustomResponse(
                general_message='You do not have permission to view analytics for this event.'
            ).get_failure_response()

        # ── Linked tasks ─────────────────────────────────────────
        linked_tasks = TaskList.objects.filter(event_fk=event)
        total_tasks = linked_tasks.count()
        approved_tasks = linked_tasks.filter(approval_status='approved').count()
        pending_tasks = linked_tasks.filter(approval_status='pending').count()

        # ── Interest stats ───────────────────────────────────────
        interests = EventInterest.objects.filter(event=event)
        total_interests = interests.count()

        # ── RSVP / attendance stats (PRD §8.3 — event analytics: RSVPs,
        # attendance, repeat attendance) ──────────────────────────
        tickets = EventConnection.objects.filter(event=event, entity_type=EventConnection.EntityType.USER_TICKET)
        total_rsvps = tickets.count()
        attendee_ids = list(tickets.filter(ticket_status=EventConnection.TicketStatus.ACTIVE).values_list("entity_id", flat=True))
        total_attendance = len(attendee_ids)
        attendance_rate = f"{(total_attendance / total_rsvps * 100):.2f}%" if total_rsvps > 0 else "0.00%"

        repeat_attendees = 0
        if attendee_ids:
            repeat_attendees = EventConnection.objects.filter(
                entity_type=EventConnection.EntityType.USER_TICKET,
                ticket_status=EventConnection.TicketStatus.ACTIVE,
                entity_id__in=attendee_ids,
            ).exclude(event=event).values("entity_id").distinct().count()

        # ── Learner satisfaction (structured feedback, PRD §13) ───
        from db.company import CompanyFeedback
        from django.db.models import Avg
        feedback_agg = CompanyFeedback.objects.filter(
            interaction_type=CompanyFeedback.InteractionType.EVENT, entity_id=event.id,
        ).aggregate(avg=Avg("rating"), count=Count("id"))

        # Interest trend (day-by-day)
        interest_trend = list(
            interests.annotate(
                date=TruncDate('expressed_at')
            ).values('date').annotate(
                count=Count('id')
            ).order_by('date')
        )
        # Format dates to ISO strings
        interest_trend = [
            {
                'date': item['date'].isoformat() if item['date'] else None,
                'count': item['count'],
            }
            for item in interest_trend
        ]

        # ── Task completion stats (from KarmaActivityLog) ────────
        task_ids = list(linked_tasks.values_list('id', flat=True))

        completion_logs = KarmaActivityLog.objects.filter(
            task_id__in=task_ids,
            appraiser_approved=True,
        )

        total_completions = completion_logs.count()
        total_karma_awarded = completion_logs.aggregate(
            total=Sum('karma')
        )['total'] or 0

        # Group and aggregate completions and karma per task
        completions_aggregate = completion_logs.values('task_id').annotate(
            completions_count=Count('id'),
            total_karma=Sum('karma')
        )
        # Build a map of task_id -> {completions_count, total_karma} for O(1) lookups
        task_stats = {
            str(item['task_id']): {
                'completions_count': item['completions_count'],
                'total_karma': item['total_karma'] or 0
            }
            for item in completions_aggregate
        }

        # Per-task breakdown
        task_breakdown = []
        for task in linked_tasks.select_related('type'):
            stats = task_stats.get(str(task.id), {'completions_count': 0, 'total_karma': 0})
            task_breakdown.append({
                'task_id': str(task.id),
                'title': task.title,
                'hashtag': task.hashtag,
                'karma': task.karma,
                'approval_status': task.approval_status,
                'completions': stats['completions_count'],
                'total_karma_awarded': stats['total_karma'],
            })

        return CustomResponse(
            general_message='Event analytics retrieved.',
            response={
                'summary': {
                    'total_interests': total_interests,
                    'total_tasks': total_tasks,
                    'approved_tasks': approved_tasks,
                    'pending_tasks': pending_tasks,
                    'total_task_completions': total_completions,
                    'total_karma_awarded': total_karma_awarded,
                    'total_rsvps': total_rsvps,
                    'total_attendance': total_attendance,
                    'attendance_rate': attendance_rate,
                    'repeat_attendees': repeat_attendees,
                    'learner_satisfaction': {
                        'average_rating': round(feedback_agg['avg'], 2) if feedback_agg['avg'] else None,
                        'rating_count': feedback_agg['count'] or 0,
                    },
                },
                'interest_trend': interest_trend,
                'task_breakdown': task_breakdown,
            },
        ).get_success_response()
