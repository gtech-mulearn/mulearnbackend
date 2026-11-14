import uuid
from db.task import KarmaActivityLog, TaskList, Wallet
from db.user import User
from utils.utils import DateTimeUtils
from django.db.models import F


def notify_karma_change(notif_type, recipient_id, actor_id, task_title, karma, kal_id):
    """
    Fire an individual KARMA_AWARDED/KARMA_REMOVED notification for one
    KarmaActivityLog row. Shared by every karma-writing call site in the
    codebase (utils/karma.py's own add_karma/remove_karma, plus the Intern
    module's direct KarmaActivityLog writes) so they all get the same
    behavior without duplicating the dispatch() call at each site.

    Self-triggered actions (recipient awarding karma to themselves, e.g.
    creating a Learning Circle or joining a meeting) must still notify —
    dispatch() auto-excludes the actor from the audience, and here the
    audience IS the actor, so passing actor_id in that case would silently
    drop the only recipient. Only pass it through when someone else is
    actually the one who triggered it.
    """
    from api.notification.service import NotificationService
    from api.notification.audience import Audience

    effective_actor = (
        str(actor_id)
        if actor_id and str(actor_id) != str(recipient_id)
        else None
    )
    NotificationService.dispatch(
        notif_type = notif_type,
        audience   = Audience.user(str(recipient_id)),
        context    = {"karma": karma, "reason": task_title},
        entity_id  = str(kal_id),
        occurrence = "1",
        actor_id   = effective_actor,
    )


def add_karma(
    user_id: str | list[str], hashtag: str, approved_by: str, karma: int | None = None
):
    from api.notification.types import NotificationType

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
        kal_rows = [
            KarmaActivityLog(
                id=str(uuid.uuid4()),
                user_id=uid,
                karma=karma,
                task=task,
                updated_by_id=uid,
                created_by_id=uid,
                appraiser_approved=True,
                peer_approved=True,
                appraiser_approved_by_id=approved_by,
                peer_approved_by_id=approved_by,
                task_message_id="none",
                lobby_message_id="none",
                dm_message_id="none",
            )
            for uid in user_ids
        ]
        KarmaActivityLog.objects.bulk_create(kal_rows)
        Wallet.objects.filter(user_id__in=user_ids).update(
            karma=F("karma") + karma,
            karma_last_updated_at=DateTimeUtils.get_current_utc_time(),
            updated_at=DateTimeUtils.get_current_utc_time(),
        )
        for row in kal_rows:
            notify_karma_change(
                NotificationType.KARMA_AWARDED, row.user_id, approved_by, task.title, karma, row.id
            )
    else:
        if not User.objects.filter(id=user_id).exists():
            return False
        kal = KarmaActivityLog.objects.create(
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

        notify_karma_change(
            NotificationType.KARMA_AWARDED, user_id, approved_by, task.title, karma, kal.id
        )
    return True


def remove_karma(
    user_id: str | list[str], hashtag: str, karma: int | None = None, removed_by: str | None = None
):
    """Reverse karma awarded for a given hashtag (e.g. on report deletion)."""
    from api.notification.types import NotificationType

    task = TaskList.objects.filter(hashtag=hashtag).first()
    if not task:
        return False
    if not karma:
        karma = task.karma
    user_ids = user_id if isinstance(user_id, list) else [user_id]
    if User.objects.filter(id__in=user_ids).count() != len(user_ids):
        return False
    for uid in user_ids:
        latest = (
            KarmaActivityLog.objects.filter(user_id=uid, task=task)
            .order_by("-created_at")
            .first()
        )
        if latest:
            kal_id = latest.id
            latest.delete()
            notify_karma_change(
                NotificationType.KARMA_REMOVED, uid, removed_by, task.title, karma, kal_id
            )
    Wallet.objects.filter(user_id__in=user_ids).update(
        karma=F("karma") - karma,
        karma_last_updated_at=DateTimeUtils.get_current_utc_time(),
        updated_at=DateTimeUtils.get_current_utc_time(),
    )
    return True
