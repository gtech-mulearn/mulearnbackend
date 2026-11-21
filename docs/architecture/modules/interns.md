# `interns`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

The intern guild: intern tasks, daily timesheets, weekly reviews, leave and guild minutes.

## Kind

Supporting.

## Tables it owns

`user_intern_guild_link`, `intern_task`, `intern_daily_timesheet`, `intern_weekly_review`, `intern_leave_request`, `intern_guild_minute`.

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `intern_daily_timesheet` | `api/dashboard/intern/timesheet/serializers.py` :: `create`<br>`api/dashboard/intern/timesheet/timesheet_views.py` :: `patch`<br>`api/dashboard/intern/timesheet/timesheet_views.py` :: `post`<br>`api/dashboard/manage_interns/reviews/review_views.py` :: `patch` | — |
| `intern_guild_minute` | `api/dashboard/intern/minutes/minutes_views.py` :: `delete`<br>`api/dashboard/intern/minutes/minutes_views.py` :: `post`<br>`api/dashboard/intern/minutes/minutes_views.py` :: `put` | — |
| `intern_leave_request` | `api/dashboard/intern/leave/leave_views.py` :: `patch`<br>`api/dashboard/intern/leave/leave_views.py` :: `post`<br>`api/dashboard/intern/leave/serializers.py` :: `create`<br>`api/dashboard/manage_interns/leave/leave_views.py` :: `patch` | — |
| `intern_task` | `api/dashboard/intern/tasks/tasks_views.py` :: `patch`<br>`api/dashboard/intern/timesheet/serializers.py` :: `create`<br>`api/dashboard/intern/timesheet/timesheet_views.py` :: `patch`<br>`api/dashboard/manage_interns/tasks/serializers.py` :: `create`<br>`api/dashboard/manage_interns/tasks/serializers.py` :: `update`<br>`api/dashboard/manage_interns/tasks/tasks_views.py` :: `delete`<br>`api/dashboard/manage_interns/tasks/tasks_views.py` :: `patch`<br>`api/dashboard/manage_interns/tasks/tasks_views.py` :: `post`<br>`mu_celery/intern_cron.py` :: `intern_task_deadline_cron` | — |
| `intern_weekly_review` | `api/dashboard/intern/weekly_review/serializers.py` :: `create`<br>`api/dashboard/intern/weekly_review/serializers.py` :: `update`<br>`api/dashboard/intern/weekly_review/weekly_review_views.py` :: `patch`<br>`api/dashboard/intern/weekly_review/weekly_review_views.py` :: `post`<br>`api/dashboard/manage_interns/reviews/review_views.py` :: `patch` | — |
| `user_intern_guild_link` | `api/dashboard/manage_interns/interns_views.py` :: `delete`<br>`api/dashboard/manage_interns/interns_views.py` :: `patch`<br>`api/dashboard/manage_interns/interns_views.py` :: `post`<br>`api/dashboard/manage_interns/leave/leave_views.py` :: `patch`<br>`api/dashboard/manage_interns/reviews/review_views.py` :: `patch`<br>`api/dashboard/manage_interns/serializers.py` :: `create`<br>`api/dashboard/manage_interns/serializers.py` :: `update`<br>`api/dashboard/roles/dash_roles_serializer.py` :: `create`<br>`api/dashboard/roles/dash_roles_views.py` :: `delete`<br>`mu_celery/intern_cron.py` :: `intern_daily_status_cron` | — |

## Public API (public.py)

`guild_of(user_id)`.

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `interns.intern_work_approved` (`contributions` awards the karma; `gamification` updates streaks) | none |

## Allowed dependencies

`people.public`, `identity_access.public`.

## What moves from legacy code

- `api/dashboard/manage_interns/`, `api/dashboard/intern/`, `mu_celery/intern_cron.py`
- the intern karma writes move to `contributions` in issue 0097

## Cut-over steps

1. [0097](../github-issues/0097-move-intern-karma-writes.md): Move intern karma writes onto contributions (Phase 4)
1. [Epic: Later: modules on demand and deferred items](../github-issues/epics/later-on-demand.md)

## Tests this module needs

- An approved review produces one award, even when the request is retried.

## Open questions

- The roles for intern administration move onto scoped grants in Phase 5.
