"""
Daily timesheet streak (shown on the leaderboard) and the Quest Log entry.

Moved from api/dashboard/intern/manage/reviews/review_views.py when admin
approval of daily timesheets was removed. Every timesheet counts (there is no
status column any more; was APPROVED only). Streak milestones no longer pay
karma: the streak is only stored for the leaderboard.
"""
import uuid

from django.db.models import F
from django.utils.timezone import now

from api.notification.types import NotificationType
from db.achievement import UserStreak
from db.intern import InternDailyTimesheet, UserInternTeamLink
from db.task import KarmaActivityLog, TaskList, Wallet
from utils.karma import notify_karma_change
from utils.types import InternHashtag

TIMESHEET_STREAK_TYPE = 'intern_timesheet'


def recalculate_intern_timesheet_streak(user_id: str) -> dict:
    """
    Recalculates the intern_timesheet streak from scratch by looking at the
    entire history of counted timesheets, sorted chronologically.

    This is order-independent: the result is identical regardless of the
    order the timesheets were submitted.

    Returns:
        dict with keys:
            - current_streak (int): The streak ending at the latest entry_date
            - longest_streak (int): The overall longest continuous streak
            - last_active (date | None): The most recent counted entry_date
    """
    counted_dates = list(
        InternDailyTimesheet.objects.filter(user_id=user_id)
        .order_by('entry_date')
        .values_list('entry_date', flat=True)
        .distinct()  # Guard against duplicate rows for the same date
    )

    if not counted_dates:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'last_active': None,
        }

    current = 1
    longest = 1

    for i in range(1, len(counted_dates)):
        prev = counted_dates[i - 1]
        curr = counted_dates[i]
        diff = (curr - prev).days

        # Consecutive: next calendar day, OR Friday→Monday (skipping weekend)
        is_consecutive = (
            diff == 1 or
            (diff == 3 and curr.weekday() == 0 and prev.weekday() == 4)
        )

        if is_consecutive:
            current += 1
        elif diff > 0:
            # Gap — streak resets
            current = 1
        # diff == 0 means duplicate date (already deduped, but just in case)

        longest = max(longest, current)

    return {
        'current_streak': current,
        'longest_streak': longest,
        'last_active': counted_dates[-1],
    }


def log_daily_timesheet_activity(user_id: str):
    """
    Writes the #intern-daily-log activity row so the submission appears in the
    intern's Quest Log (overview/activity reads #intern-* karma logs).

    Base daily-log karma is InternHashtag.DAILY_LOG_KARMA (currently 0). The
    wallet is only touched and a notification only sent when that is > 0, so
    a 0-karma submission no longer produces a "you got 0 karma" notification.
    """
    task_list = TaskList.objects.filter(hashtag=InternHashtag.DAILY_LOG_HASHTAG.value).first()
    if not task_list:
        return

    karma = InternHashtag.DAILY_LOG_KARMA.value
    kal = KarmaActivityLog.objects.create(
        id=str(uuid.uuid4()),
        user_id=user_id,
        task=task_list,
        karma=karma,
        appraiser_approved=True,
        updated_by_id=user_id,
        updated_at=now(),
        created_by_id=user_id,
        created_at=now(),
    )

    if karma > 0:
        wallet, _ = Wallet.objects.get_or_create(
            user_id=user_id,
            defaults={'created_by_id': user_id, 'updated_by_id': user_id}
        )
        Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + karma)
        notify_karma_change(
            NotificationType.KARMA_AWARDED, user_id, user_id, task_list.title, karma, kal.id
        )


def sync_timesheet_streak(user_id: str) -> dict:
    """
    Recomputes the intern's timesheet streak and stores it (the leaderboard
    reads it). No karma is paid for streak milestones.

    It does not change the intern's status. intern_daily_status_cron is the
    only place that sets ACTIVE / AT_RISK / INACTIVE: it skips today and
    yesterday, so a status set here would be undone by the next run.

    Safe to call repeatedly: the streak is recomputed from scratch.

    Locks the intern's team membership rows for the duration of the caller's
    transaction so two concurrent submissions by the same intern write the
    streak one after the other. Must be called inside transaction.atomic().
    """
    # Taken only for the row lock; the rows themselves aren't used.
    list(UserInternTeamLink.objects.select_for_update().filter(user_id=user_id).values_list('id', flat=True))

    recalc = recalculate_intern_timesheet_streak(user_id)

    streak, _ = UserStreak.objects.get_or_create(user_id=user_id, streak_type=TIMESHEET_STREAK_TYPE)
    streak.current_streak = recalc['current_streak']
    streak.longest_streak = recalc['longest_streak']
    streak.last_active = recalc['last_active']
    streak.save()

    return recalc
