import uuid
from db.task import KarmaActivityLog, TaskList, Wallet
from db.user import User
from utils.utils import DateTimeUtils
from django.db.models import F


def add_karma(
    user_id: str | list[str], hashtag: str, approved_by: str, karma: int | None = None
):
    task = TaskList.objects.filter(hashtag=hashtag).first()
    if not task:
        return False
    if not karma:
        karma = task.karma
    if not User.objects.filter(id=approved_by).exists():
        return False
    if isinstance(user_id, list):
        count = User.objects.filter(id__in=user_id).count()
        if count != len(user_id):
            return False
        user_ids = user_id
        KarmaActivityLog.objects.bulk_create(
            [
                KarmaActivityLog(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    karma=karma,
                    task=task,
                    updated_by_id=user_id,
                    created_by_id=user_id,
                    appraiser_approved=True,
                    peer_approved=True,
                    appraiser_approved_by_id=approved_by,
                    peer_approved_by_id=approved_by,
                    task_message_id="none",
                    lobby_message_id="none",
                    dm_message_id="none",
                )
                for user_id in user_ids
            ]
        )
        Wallet.objects.filter(user_id__in=user_ids).update(
            karma=F("karma") + karma,
            karma_last_updated_at=DateTimeUtils.get_current_utc_time(),
            updated_at=DateTimeUtils.get_current_utc_time(),
        )
    else:
        if not User.objects.filter(id=user_id).exists():
            return False
        KarmaActivityLog.objects.create(
            id=str(uuid.uuid4()),
            user_id=user_id,
            karma=karma,
            task=task,
            updated_by_id=user_id,
            created_by_id=user_id,
            appraiser_approved=True,
            peer_approved=True,
            appraiser_approved_by_id=approved_by,
            peer_approved_by_id=approved_by,
            task_message_id="none",
            lobby_message_id="none",
            dm_message_id="none",
        )

        wallet = Wallet.objects.filter(user_id=user_id).first()
        wallet.karma += karma
        wallet.karma_last_updated_at = DateTimeUtils.get_current_utc_time()
        wallet.updated_at = DateTimeUtils.get_current_utc_time()
        wallet.save()
    return True
