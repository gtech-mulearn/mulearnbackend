from rest_framework.views import APIView
from db.notification import Notification
from db.user import User
from utils.permission import CustomizePermission, JWTUtils, RoleRequired
from utils.response import CustomResponse
from utils.types import RoleType
from utils.utils import DateTimeUtils
import uuid
from . import serializers


class NotificationListsAPI(APIView):
    def get(self, request):
        """
        Get all notifications for a user
        Args:
            request:

        Returns:
            200: List of notifications

        """
        user_id = JWTUtils.fetch_user_id(request)
        notification_list = Notification.objects.filter(user_id=user_id)
        response = serializers.NotificationSerializer(notification_list, many=True).data
        return CustomResponse(response=response).get_success_response()


class NotificationDeleteAPI(APIView):
    authentication_classes = [CustomizePermission]

    def delete(self, request, notification_id):
        """
        Delete notification by providing notification id
        Args:
            notification_id:
            request: 'notification_id'

        Returns:
            200: Notification deleted successfully
            400: Notification not found

        """
        user_id = JWTUtils.fetch_user_id(request)
        notification = Notification.objects.filter(user_id=user_id, id=notification_id)
        if not notification:
            return CustomResponse(general_message='Notification not found').get_failure_response()

        notification.delete()
        return CustomResponse(general_message='Notification deleted successfully').get_success_response()


class NotificationDeleteAllAPI(APIView):
    authentication_classes = [CustomizePermission]

    def delete(self, request):
        """
        Delete all the notifications for a user
        Args:
            request:

        Returns:
            200: Notification deleted successfully
            400: Notification not found

        """
        user_id = JWTUtils.fetch_user_id(request)
        notification = Notification.objects.filter(user_id=user_id)
        if not notification:
            return CustomResponse(general_message='Notifications are empty').get_failure_response()

        notification.delete()
        return CustomResponse(general_message='All notification deleted successfully').get_success_response()


class NotificationCreateAPI(APIView):
    authentication_classes = [CustomizePermission]

    @RoleRequired([RoleType.ADMIN.value])
    def post(self, request):
        admin_id = JWTUtils.fetch_user_id(request)
        admin = User.objects.get(id=admin_id)

        title = request.data.get('title')
        description = request.data.get('description')
        button = request.data.get('button')
        url = request.data.get('url')
        scope = request.data.get('scope')

        if not all([title, description, scope]):
            return CustomResponse(general_message="Title, description and scope are required").get_failure_response()

        if scope == 'global':
            user_ids = User.objects.values_list('id', flat=True)
        elif scope == 'campus':
            campus_id = request.data.get('campus')
            if not campus_id:
                return CustomResponse(general_message="Campus ID is required for campus scope").get_failure_response()
            user_ids = User.objects.filter(user_organization_link_user__org_id=campus_id).values_list('id', flat=True).distinct()
        elif scope == 'ig':
            ig_id = request.data.get('ig')
            if not ig_id:
                return CustomResponse(general_message="IG ID is required for IG scope").get_failure_response()
            user_ids = User.objects.filter(user_ig_link_user__ig_id=ig_id).values_list('id', flat=True).distinct()
        else:
            return CustomResponse(general_message="Invalid scope").get_failure_response()

        current_time = DateTimeUtils.get_current_utc_time()
        notifications = [
            Notification(
                id=uuid.uuid4(),
                user_id=uid,
                title=title,
                description=description,
                button=button,
                url=url,
                created_at=current_time,
                created_by=admin
            )
            for uid in user_ids
        ]

        Notification.objects.bulk_create(notifications)

        return CustomResponse(general_message="Notification created successfully").get_success_response()
