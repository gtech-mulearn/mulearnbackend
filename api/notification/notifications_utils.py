from django.db import IntegrityError
from db.notification import Notification
import logging

logger = logging.getLogger(__name__)


class NotificationUtils:
    """
    Utility class for Notification
    """

    @staticmethod
    def insert_notification(user_id, title, description, button, url, created_by):
        """
        Insert notification

        Args:
            user_id:
            title:
            description:
            button:
            url:
            created_by:

        Returns:
            True if the notification is inserted successfully, False otherwise.
        """
        try:
            notification = Notification.objects.create(
                user_id=user_id,
                title=title,
                description=description,
                button=button,
                url=url,
                created_by=created_by,
                )
            notification.save()
            return True
        except IntegrityError as e:
            logger.error(e)
            return False