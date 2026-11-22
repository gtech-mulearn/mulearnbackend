"""Celery queues and task routes (issue 0064, ADR-042).

Every task goes to a named queue, so a bulk job can't delay time-sensitive work. A worker group
per queue family runs in deployed environments (issues 0078 and 0105). Until then, a worker
started without -Q consumes every declared queue, which is what deployed workers do today.

Routes are exact task names or one glob per mu_celery module, and no task may match two.
tests/architecture/test_task_routing.py fails when a registered task has no route.
"""

from fnmatch import fnmatchcase

QUEUES = ("critical", "default", "projections", "notifications", "bulk", "integrations")

# Celery's queue before this change. Workers keep consuming it so that messages sent to it by
# an older process during a rolling deploy still run; nothing routes to it. Remove it a
# release after this ships.
LEGACY_QUEUE = "celery"

# "critical" and "integrations" have no tasks yet: OTP mail is sent by the auth server, and the
# Discord work isn't a Celery task.
TASK_ROUTES = {
    # notifications
    "mu_celery.push_tasks.*": {"queue": "notifications"},
    "mu_celery.task.send_email": {"queue": "notifications"},
    # projections: aggregates and leaderboards that can be rebuilt
    "mu_celery.org_aggregates_cron.*": {"queue": "projections"},
    "mu_celery.learning_circle_aggregates_cron.*": {"queue": "projections"},
    "mu_celery.leaderboard_cron.*": {"queue": "projections"},
    # bulk: media and other heavy jobs
    "mu_celery.media_content_tasks.*": {"queue": "bulk"},
    "mu_celery.achievement_tasks.bulk_check_and_issue_achievements": {"queue": "bulk"},
    "mu_celery.achievement_cron.backfill_missing_aggregates": {"queue": "bulk"},
    "mu_celery.achievement_cron.integrity_check": {"queue": "bulk"},
    # default: everything else
    "mu_celery.achievement_cron.evaluate_daily_streaks": {"queue": "default"},
    "mu_celery.achievement_tasks.process_achievement_event": {"queue": "default"},
    "mu_celery.achievement_tasks.issue_vc_async": {"queue": "default"},
    "mu_celery.alumni_cron.*": {"queue": "default"},
    "mu_celery.company_tasks.*": {"queue": "default"},
    "mu_celery.event_cron.*": {"queue": "default"},
    "mu_celery.intern_cron.*": {"queue": "default"},
    "mu_celery.mentor_tasks.*": {"queue": "default"},
    "mu_celery.task.onboard_user": {"queue": "default"},
}


def matching_routes(task_name: str) -> list[str]:
    """The TASK_ROUTES keys that match ``task_name``, exactly or as a glob."""
    return [pattern for pattern in TASK_ROUTES if fnmatchcase(task_name, pattern)]


def unrouted(task_names) -> list[str]:
    """The task names no route matches. Celery's built-in tasks (celery.*) are ignored."""
    return sorted(name for name in task_names if not name.startswith("celery.") and not matching_routes(name))
