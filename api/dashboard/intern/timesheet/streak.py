"""
Daily timesheet streak + milestone karma.

Moved from api/dashboard/manage_interns/reviews/review_views.py when admin
approval of daily timesheets was removed. The streak and milestone logic is
unchanged; the only differences are:
  - timesheets with any status in COUNTED_TIMESHEET_STATUSES count (was APPROVED only)
  - the karma actor is whoever triggers the sync (the intern on submit),
    since there is no approving admin any more.
"""
import uuid

from django.db.models import F
from django.utils.timezone import now

from api.notification.types import NotificationType
from db.achievement import UserStreak
from db.intern import InternDailyTimesheet, UserInternGuildLink
from db.task import KarmaActivityLog, TaskList, Wallet
from utils.karma import notify_karma_change
from utils.types import COUNTED_TIMESHEET_STATUSES, InternHashtag

TIMESHEET_STREAK_TYPE = 'intern_timesheet'

TIMESHEET_MILESTONE_MAP = {
    7:  (InternHashtag.STREAK_7_HASHTAG.value,  InternHashtag.STREAK_7_KARMA.value),
    14: (InternHashtag.STREAK_14_HASHTAG.value, InternHashtag.STREAK_14_KARMA.value),
    30: (InternHashtag.STREAK_30_HASHTAG.value, InternHashtag.STREAK_30_KARMA.value),
    60: (InternHashtag.STREAK_60_HASHTAG.value, InternHashtag.STREAK_60_KARMA.value),
    90: (InternHashtag.STREAK_90_HASHTAG.value, InternHashtag.STREAK_90_KARMA.value),
}


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
            - milestone_hits (dict): {milestone_days: count_of_times_reached}
    """
    counted_dates = list(
        InternDailyTimesheet.objects.filter(
            user_id=user_id,
            status__in=COUNTED_TIMESHEET_STATUSES,
        )
        .order_by('entry_date')
        .values_list('entry_date', flat=True)
        .distinct()  # Guard against duplicate rows for the same date
    )

    if not counted_dates:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'last_active': None,
            'milestone_hits': {},
        }

    milestones = list(TIMESHEET_MILESTONE_MAP.keys())
    milestone_hits = {m: 0 for m in milestones}

    current = 1
    longest = 1
    for m in milestones:
        if current >= m:
            milestone_hits[m] += 1

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
        for m in milestones:
            if current == m:
                milestone_hits[m] += 1

    return {
        'current_streak': current,
        'longest_streak': longest,
        'last_active': counted_dates[-1],
        'milestone_hits': milestone_hits,
    }


def _award_missing_milestone_karma(user_id: str, actor_id: str, milestone_hits: dict, milestone_map: dict):
    """
    Awards milestone karma for any gaps between expected and actual hits.

    Uses "Expected vs Actual" logic:
      - expected_hits: how many times the streak crossed a milestone (from recalculation)
      - actual_hits:   how many times we already gave karma for that milestone

    Only awards the *difference*, so this is idempotent and safe to call on
    every submission regardless of order.

    Args:
        user_id:        The intern's user ID
        actor_id:       Who triggered the award (used as created_by)
        milestone_hits: {milestone_days: expected_hit_count} from recalculate_*
        milestone_map:  {milestone_days: (hashtag, bonus_karma)}
    """
    for milestone_days, (hashtag, bonus_karma) in milestone_map.items():
        expected = milestone_hits.get(milestone_days, 0)
        if expected == 0:
            continue

        task_list = TaskList.objects.filter(hashtag=hashtag).first()
        if not task_list:
            continue

        actual = KarmaActivityLog.objects.filter(
            user_id=user_id,
            task=task_list,
            appraiser_approved=True,
        ).count()

        missing = expected - actual
        if missing <= 0:
            continue

        wallet, _ = Wallet.objects.get_or_create(
            user_id=user_id,
            defaults={'created_by_id': actor_id, 'updated_by_id': actor_id}
        )

        for _ in range(missing):
            kal = KarmaActivityLog.objects.create(
                id=str(uuid.uuid4()),
                user_id=user_id,
                task=task_list,
                karma=bonus_karma,
                appraiser_approved=True,
                updated_by_id=actor_id,
                updated_at=now(),
                created_by_id=actor_id,
                created_at=now(),
            )
            notify_karma_change(
                NotificationType.KARMA_AWARDED, user_id, actor_id, task_list.title, bonus_karma, kal.id
            )
        Wallet.objects.filter(id=wallet.id).update(karma=F('karma') + (bonus_karma * missing))


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


def sync_timesheet_streak(user_id: str, actor_id: str) -> dict:
    """
    Recomputes the intern's timesheet streak, stores it, awards any milestone
    karma not yet paid.

    It does not change the intern's status. intern_daily_status_cron is the
    only place that sets ACTIVE / AT_RISK / INACTIVE: it skips today and
    yesterday, so a status set here would be undone by the next run.

    Runs the same steps the admin approval used to run. Safe to call
    repeatedly — streak is recomputed from scratch and milestones are
    awarded expected-vs-actual.

    Locks the intern's guild-link row for the duration of the caller's
    transaction so two concurrent submissions by the same intern cannot both
    see the same milestone as unpaid and award it twice. Must be called
    inside transaction.atomic().
    """
    # Taken only for the row lock; the row itself isn't used.
    UserInternGuildLink.objects.select_for_update().filter(user_id=user_id).first()

    recalc = recalculate_intern_timesheet_streak(user_id)

    streak, _ = UserStreak.objects.get_or_create(user_id=user_id, streak_type=TIMESHEET_STREAK_TYPE)
    streak.current_streak = recalc['current_streak']
    streak.longest_streak = recalc['longest_streak']
    streak.last_active = recalc['last_active']
    streak.save()

    _award_missing_milestone_karma(user_id, actor_id, recalc['milestone_hits'], TIMESHEET_MILESTONE_MAP)

    return recalc
