from rest_framework.views import APIView

from db.notification import Notification
from utils.permission import CustomizePermission, JWTUtils
from utils.response import CustomResponse
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
            return CustomResponse(response='Notification not found').get_failure_response()

        notification.delete()
        return CustomResponse(response='Notification deleted successfully').get_success_response()


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
            return CustomResponse(response='Notifications are empty').get_failure_response()

        notification.delete()
        return CustomResponse(response='All notification deleted successfully').get_success_response()
