from django.utils import timezone
from rest_framework.views import APIView

from db.notification import Notification, BroadcastNotification
from db.events import EventConnection, EventInterest
from utils.permission import CustomizePermission, JWTUtils, role_required
from utils.response import CustomResponse
from utils.types import RoleType
from . import serializers
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers as s


def _resolve_user_broadcasts(user_id: str):
    """
    Return active (non-expired) BroadcastNotification rows that the user belongs to.

    Audience matching logic per target_type:
        'global'          -> always included
        'campus'          -> user is linked to that org (UserOrganizationLink)
        'interest_group'  -> user has an active LEARNER link to that IG (UserIgLink)
        'campus_ig'       -> user has an active LEARNER link and is in that campus org
        'event_interest'  -> user has expressed interest in that event (EventInterest)
        'event_coowners'  -> user is the event creator OR a CO_OWNER EventConnection
    """
    from db.organization import UserOrganizationLink
    from db.task import UserIgLink

    now = timezone.now()
    active_broadcasts = BroadcastNotification.objects.filter(expires_at__gt=now)

    # --- Collect the user's memberships for efficient filtering ---

    # Campus org IDs
    campus_org_ids = set(
        UserOrganizationLink.objects.filter(
            user_id=user_id, verified=True
        ).values_list('org_id', flat=True)
    )

    # Active learner IG IDs
    learner_ig_ids = set(
        UserIgLink.objects.filter(
            user_id=user_id,
            assignment_type=UserIgLink.AssignmentType.LEARNER,
            is_active=True,
        ).values_list('ig_id', flat=True)
    )

    # Events the user expressed interest in
    interested_event_ids = set(
        EventInterest.objects.filter(user_id=user_id).values_list('event_id', flat=True)
    )

    # Events the user co-owns
    coowned_event_ids = set(
        EventConnection.objects.filter(
            entity_id=user_id,
            entity_type=EventConnection.EntityType.CO_OWNER,
        ).values_list('event_id', flat=True)
    )

    # Events the user created
    from db.events import Event
    created_event_ids = set(
        Event.objects.filter(created_by_id=user_id).values_list('id', flat=True)
    )

    # All events where user is creator or co-owner (for event_coowners type)
    event_coowner_ids = coowned_event_ids | created_event_ids

    matched = []
    for b in active_broadcasts:
        tt = b.target_type
        tid = b.target_id

        if tt == 'global':
            matched.append(b)
        elif tt == 'campus' and tid in campus_org_ids:
            matched.append(b)
        elif tt == 'interest_group' and tid in learner_ig_ids:
            matched.append(b)
        elif tt == 'campus_ig':
            # Resolve the CampusIGChapter to check if the user is in both the org and the ig of that chapter
            from db.campus import CampusIGChapter
            chapter = CampusIGChapter.objects.filter(id=tid).first()
            if chapter and chapter.org_id in campus_org_ids and chapter.ig_id in learner_ig_ids:
                matched.append(b)
        elif tt == 'event_interest' and tid in interested_event_ids:
            matched.append(b)
        elif tt == 'event_coowners' and tid in event_coowner_ids:
            matched.append(b)

    return matched


class NotificationListsAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Notification'],
        description=(
            "Retrieve all notifications for the authenticated user. "
            "Returns two lists: `direct` (personal) and `broadcasts` (group/audience)."
        ),
        responses={200: inline_serializer(
            name='NotificationListResponse',
            fields={
                'direct':     serializers.NotificationSerializer(many=True),
                'broadcasts': serializers.BroadcastNotificationSerializer(many=True),
            },
        )},
    )
    def get(self, request):
        """
        Returns:
            direct:     Personal notifications addressed to this user.
            broadcasts: Active group-wide notifications the user qualifies for,
                        resolved by audience membership at read time.
        """
        user_id = JWTUtils.fetch_user_id(request)

        direct_qs = Notification.objects.filter(user_id=user_id)
        broadcast_list = _resolve_user_broadcasts(user_id)

        return CustomResponse(response={
            'direct':     serializers.NotificationSerializer(direct_qs, many=True).data,
            'broadcasts': serializers.BroadcastNotificationSerializer(broadcast_list, many=True).data,
        }).get_success_response()


class NotificationDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete Notification Delete.",
        responses={200: serializers.NotificationSerializer},
    )
    def delete(self, request, notification_id):
        """
        Delete a single direct notification by its ID.
        Broadcast notifications cannot be individually deleted;
        they expire automatically via their expires_at timestamp.
        """
        user_id = JWTUtils.fetch_user_id(request)
        notification = Notification.objects.filter(user_id=user_id, id=notification_id)
        if not notification:
            return CustomResponse(general_message='Notification not found').get_failure_response()

        notification.delete()
        return CustomResponse(general_message='Notification deleted successfully').get_success_response()


class NotificationDeleteAllAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(tags=['Notification'], description="Delete Notification Delete All.",
        responses={200: serializers.NotificationSerializer},
    )
    def delete(self, request):
        """
        Delete all direct notifications for the authenticated user.
        Broadcast notifications are unaffected.
        """
        user_id = JWTUtils.fetch_user_id(request)
        notification = Notification.objects.filter(user_id=user_id)
        if not notification:
            return CustomResponse(general_message='Notifications are empty').get_failure_response()

        notification.delete()
        return CustomResponse(general_message='All notification deleted successfully').get_success_response()


class BroadcastNotificationDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Notification'],
        description="Delete a single broadcast notification by its ID. Admin role required.",
        responses={200: serializers.BroadcastNotificationSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def delete(self, request, broadcast_id):
        """
        Delete a single BroadcastNotification by its ID.
        Only accessible to users with the Admin role.
        """
        try:
            broadcast = BroadcastNotification.objects.get(id=broadcast_id)
        except BroadcastNotification.DoesNotExist:
            return CustomResponse(general_message='Broadcast notification not found').get_failure_response()

        broadcast.delete()
        return CustomResponse(general_message='Broadcast notification deleted successfully').get_success_response()


class BroadcastNotificationDeleteAllAPI(APIView):
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Notification'],
        description="Delete all broadcast notifications. Admin role required.",
        responses={200: serializers.BroadcastNotificationSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def delete(self, request):
        """
        Delete ALL BroadcastNotification records.
        Only accessible to users with the Admin role.
        """
        broadcasts = BroadcastNotification.objects.all()
        if not broadcasts.exists():
            return CustomResponse(general_message='No broadcast notifications to delete').get_failure_response()

        count = broadcasts.count()
        broadcasts.delete()
        return CustomResponse(
            general_message=f'All {count} broadcast notification(s) deleted successfully'
        ).get_success_response()


# ─────────────────────────────────────────────────────────────────────────────
# ADMIN BROADCAST CRUD — List / Create / Update
# ─────────────────────────────────────────────────────────────────────────────

class BroadcastNotificationListAPI(APIView):
    """
    GET /api/v1/notification/broadcast/list/all/
    Admin-only: return all BroadcastNotification records with resolved target details.
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Notification'],
        description=(
            "Admin only. List all broadcast notifications. "
            "Each record includes a `target_details` field with the resolved "
            "human-readable name of the target audience."
        ),
        responses={200: serializers.BroadcastNotificationAdminSerializer(many=True)},
    )
    @role_required([RoleType.ADMIN.value])
    def get(self, request):
        broadcasts = BroadcastNotification.objects.select_related('created_by').all()
        data = serializers.BroadcastNotificationAdminSerializer(broadcasts, many=True).data
        return CustomResponse(response=data).get_success_response()


class BroadcastNotificationCreateAPI(APIView):
    """
    POST /api/v1/notification/broadcast/create/
    Admin-only: create a new global BroadcastNotification announcement.

    Required body fields:
        title       (str, max 50)
        description (str, max 200)
        expires_at  (datetime ISO-8601)
    Optional:
        url         (str)  — deep-link path (max 100)
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Notification'],
        description="Admin only. Create a new global broadcast announcement.",
        responses={201: serializers.BroadcastNotificationAdminSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def post(self, request):
        user_id = JWTUtils.fetch_user_id(request)
        write_serializer = serializers.BroadcastNotificationWriteSerializer(data=request.data)

        if not write_serializer.is_valid():
            return CustomResponse(general_message=write_serializer.errors).get_failure_response()

        from db.user import User as UserModel
        creator = UserModel.objects.filter(id=user_id).first()
        if not creator:
            return CustomResponse(general_message='User not found').get_failure_response()

        from utils.utils import DateTimeUtils
        now = DateTimeUtils.get_current_utc_time()

        broadcast = BroadcastNotification.objects.create(
            title=write_serializer.validated_data['title'],
            description=write_serializer.validated_data['description'],
            url=write_serializer.validated_data.get('url'),
            target_type='global',
            target_id=None,
            created_by=creator,
            created_at=now,
            expires_at=write_serializer.validated_data['expires_at'],
        )

        response_data = serializers.BroadcastNotificationAdminSerializer(broadcast).data
        return CustomResponse(
            general_message='Broadcast notification created successfully.',
            response=response_data,
        ).get_success_response()


class BroadcastNotificationUpdateAPI(APIView):
    """
    PATCH /api/v1/notification/broadcast/update/id/<broadcast_id>/
    Admin-only: partially update an existing BroadcastNotification.
    All body fields are optional (partial=True).
    """
    authentication_classes = [CustomizePermission]

    @extend_schema(
        tags=['Notification'],
        description=(
            "Admin only. Partially update a broadcast notification by its ID. "
            "All fields are optional."
        ),
        responses={200: serializers.BroadcastNotificationAdminSerializer},
    )
    @role_required([RoleType.ADMIN.value])
    def patch(self, request, broadcast_id):
        try:
            broadcast = BroadcastNotification.objects.get(id=broadcast_id)
        except BroadcastNotification.DoesNotExist:
            return CustomResponse(general_message='Broadcast notification not found').get_failure_response()

        write_serializer = serializers.BroadcastNotificationWriteSerializer(
            instance=broadcast,
            data=request.data,
            partial=True,
        )

        if not write_serializer.is_valid():
            return CustomResponse(general_message=write_serializer.errors).get_failure_response()

        write_serializer.save()

        response_data = serializers.BroadcastNotificationAdminSerializer(broadcast).data
        return CustomResponse(
            general_message='Broadcast notification updated successfully.',
            response=response_data,
        ).get_success_response()
