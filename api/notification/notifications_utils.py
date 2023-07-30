import logging

from db.notification import Notification
from utils.utils import DateTimeUtils

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

        notification = Notification.objects.create(
            user_id=user_id,
            title=title,
            description=description,
            button=button,
            url=url,
            created_at=DateTimeUtils.get_current_utc_time(),
            created_by=created_by,
        )
        if notification:
            notification.save()
            return True
        else:
            return False