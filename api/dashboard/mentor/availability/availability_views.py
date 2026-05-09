import uuid
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status

from db.user import User
from db.mentor import MentorAvailabilitySlot
from utils.permission import CustomizePermission, JWTUtils
from utils.mentor_permissions import IsIGMentor, _get_persona_context
from utils.response import CustomResponse


class MentorAvailabilityView(APIView):
    """
    GET  /api/v1/dashboard/mentor/availability/
        Returns slots for the active persona IG, plus any global (ig=NULL) slots.

    POST /api/v1/dashboard/mentor/availability/
        Creates new availability slots.
        ig_id is derived from persona context — not accepted from request body.
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def get(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)
        active_ig_id = persona_ctx['ig_id']

        # Return slots matching the active IG OR global slots (ig=NULL)
        from django.db.models import Q
        slots = MentorAvailabilitySlot.objects.filter(
            mentor_user_id=user_id,
            is_active=True,
        ).filter(
            Q(ig_id=active_ig_id) | Q(ig__isnull=True)
        ).select_related('ig').order_by('weekday', 'start_time')

        slot_data = [
            {
                "id": str(s.id),
                "ig_id": str(s.ig.id) if s.ig else None,
                "ig_name": s.ig.name if s.ig else "All IGs",
                "weekday": s.weekday,
                "start_time": s.start_time.strftime('%H:%M'),
                "end_time": s.end_time.strftime('%H:%M'),
                "timezone": s.timezone,
                "is_active": s.is_active,
                "valid_from": s.valid_from.isoformat() if s.valid_from else None,
                "valid_to": s.valid_to.isoformat() if s.valid_to else None,
            }
            for s in slots
        ]

        return CustomResponse(
            general_message="Availability slots fetched.",
            response={
                "active_ig_id": active_ig_id,
                "slots": slot_data,
            }
        ).get_success_response()

    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        user = User.objects.filter(id=user_id).first()
        if not user:
            return CustomResponse(general_message="User not found.").get_failure_response()

        persona_ctx = _get_persona_context(request)
        active_ig_id = persona_ctx['ig_id']

        slots_input = request.data.get('slots', [])
        if not slots_input or not isinstance(slots_input, list):
            return CustomResponse(
                general_message="'slots' must be a non-empty list."
            ).get_failure_response()

        created = []
        errors = []

        for i, slot in enumerate(slots_input):
            weekday = slot.get('weekday')
            start_time = slot.get('start_time')
            end_time = slot.get('end_time')
            timezone_str = slot.get('timezone', 'Asia/Kolkata')
            valid_from = slot.get('valid_from')
            valid_to = slot.get('valid_to')

            if weekday is None or not start_time or not end_time:
                errors.append({"index": i, "error": "weekday, start_time, end_time are required."})
                continue

            if not (1 <= int(weekday) <= 7):
                errors.append({"index": i, "error": "weekday must be 1 (Mon) to 7 (Sun)."})
                continue

            if start_time >= end_time:
                errors.append({"index": i, "error": "start_time must be before end_time."})
                continue

            new_slot = MentorAvailabilitySlot(
                id=str(uuid.uuid4()),
                mentor_user=user,
                ig_id=active_ig_id,   # Always bound to the active persona IG
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
                timezone=timezone_str,
                valid_from=valid_from,
                valid_to=valid_to,
                created_by=user,
                updated_by=user,
            )
            new_slot.save()
            created.append(str(new_slot.id))

        return CustomResponse(
            general_message=f"{len(created)} slot(s) created.",
            response={"created_ids": created, "errors": errors}
        ).get_success_response()


class MentorAvailabilitySlotDeleteView(APIView):
    """
    DELETE /api/v1/dashboard/mentor/availability/<slot_id>/

    Only allows deletion if:
    - slot.mentor_user == request.user
    - slot.ig_id matches active persona ig OR slot.ig is NULL (global slot)
    """
    permission_classes = [CustomizePermission, IsIGMentor]

    def delete(self, request, slot_id):
        user_id = JWTUtils.fetch_user_id(request)
        persona_ctx = _get_persona_context(request)
        active_ig_id = persona_ctx['ig_id']

        from django.db.models import Q
        slot = MentorAvailabilitySlot.objects.filter(
            id=slot_id,
            mentor_user_id=user_id,
        ).filter(
            Q(ig_id=active_ig_id) | Q(ig__isnull=True)
        ).first()

        if not slot:
            return CustomResponse(
                general_message="Slot not found or access denied.",
            ).get_failure_response()

        # Soft delete: mark inactive instead of hard delete
        slot.is_active = False
        slot.updated_by_id = user_id
        slot.save(update_fields=['is_active', 'updated_by', 'updated_at'])

        return CustomResponse(
            general_message="Availability slot removed.",
            response={"slot_id": slot_id}
        ).get_success_response()
