# `gamification`

**Status at `dev` 7fd66060:** the module does not exist yet. Its tables are mapped in the legacy `db/` app, and the code that writes them is listed below.

## Purpose

Level progression, grit (inactivity decay), achievements, period totals and leaderboards. It never writes karma; it reacts to ledger events.

## Kind

**Core.**

## Tables it owns

- `level`, `level_system`, `user_lvl_link`, `user_lvl_log`, `user_ig_lvl_link`, `user_ig_lvl_log`
- `achievement`, `achievement_rule`, `achievement_event`, `achievement_eligibility_grant`, `achievement_audit_log`, `user_achievements_log`
- `user_ig_karma`, `user_daily_activity`, `user_streak`, `user_skill_progress`
- `karma_period_total`, new
- later: `board_definition`, deferred

## Who writes these tables today

Measured at `dev` 7fd66060 with an AST scan of the backend (file and function), plus other services by name.

| Table | Backend write sites at 7fd66060 (file :: function) | Other writers |
|---|---|---|
| `achievement` | `api/dashboard/achievement/achievement_views.py` :: `delete`<br>`api/dashboard/achievement/achievement_views.py` :: `post` | — |
| `achievement_audit_log` | `mu_celery/achievement_tasks.py` :: `_issue_achievement`<br>`mu_celery/achievement_tasks.py` :: `issue_vc_async`<br>`mu_celery/achievement_tasks.py` :: `revoke_achievement` | — |
| `achievement_eligibility_grant` | `mu_celery/achievement_tasks.py` :: `_claim_via_eligibility_grant`<br>`mu_celery/achievement_tasks.py` :: `grant_achievement_eligibility`<br>`mu_celery/achievement_tasks.py` :: `revoke_achievement` | — |
| `achievement_event` | `api/dashboard/achievement/achievement_events.py` :: `emit`<br>`mu_celery/achievement_tasks.py` :: `process_achievement_event` | — |
| `achievement_rule` | `api/dashboard/achievement/achievement_views.py` :: `patch`<br>`api/dashboard/achievement/achievement_views.py` :: `post` | — |
| `user_achievements_log` | `api/dashboard/achievement/achievement_views.py` :: `post`<br>`api/management/commands/generate_acheivements.py` :: `handle`<br>`mu_celery/achievement_tasks.py` :: `_issue_achievement`<br>`mu_celery/achievement_tasks.py` :: `issue_vc_async`<br>`mu_celery/achievement_tasks.py` :: `revoke_achievement` | Discord bot |
| `user_daily_activity` | `mu_celery/achievement_tasks.py` :: `_update_aggregates` | Discord bot |
| `user_ig_karma` | `mu_celery/achievement_cron.py` :: `backfill_missing_aggregates`<br>`mu_celery/achievement_tasks.py` :: `_update_aggregates` | Discord bot |
| `user_ig_lvl_link` | `api/dashboard/ig/dash_ig_view.py` :: `post`<br>`api/dashboard/profile/profile_serializer.py` :: `update` | — |
| `user_lvl_link` | `api/register/serializers.py` :: `create` | Discord bot, scheduler-service |
| `user_lvl_log` | none | Discord bot |
| `user_skill_progress` | `mu_celery/achievement_tasks.py` :: `_update_aggregates` | Discord bot |
| `user_streak` | `api/dashboard/manage_interns/reviews/review_views.py` :: `patch`<br>`mu_celery/achievement_cron.py` :: `_update_streak` | — |

## Invariants

- The level derives from the balance and the thresholds.
- At most one grit change per user per IST day.
- Only `gamification` writes level tables.
- One award per (user, achievement), already `UNIQUE`.
- A period total equals the sum of the user's entries in that IST month and can be rebuilt.

## Public API (public.py)

| Commands | Queries |
|---|---|
| `apply_karma_change(envelope)` (consumer) | `get_level(user_id)` |
| `ensure_level_progress(user_id)` (consumer of `UserRegistered`) | `board(scope, period, cursor, limit)` |
| `claim_achievement`, `issue_achievement`, `revoke_achievement` | `rank(user_id, scope, period)` |
| `rebuild_period_totals(period)` | `achievements(user_id)` |
| `run_grit_cycle(run_date)` (absorbed from the scheduler later) | |

## Events

| Publishes (v1) | Consumes (v1) |
|---|---|
| `gamification.level_changed`, `achievement_unlocked`, `achievement_revoked` | `contributions.karma_awarded`, `karma_reversed`, `karma_penalized`, `karma_adjusted` |
| `user.level_up` (integration event for `mucoin-service`, on increases only; on hold with the μCoin integration) | `people.user_registered`, `communities.ig_membership_changed`, `interns.intern_work_approved` |

## Allowed dependencies

`contributions.public` (ledger reads for rebuilds), `people.public`, `organizations.public`, `communities.public`, `identity_access.public`.

## What moves from legacy code

- `api/dashboard/achievement/`, `mu_celery/achievement_cron.py`, `mu_celery/achievement_tasks.py`
- `api/leaderboard/`, `mu_celery/leaderboard_cron.py`, `api/top100_coders/`
- the level writes in the Discord bot and the grit meter in `scheduler-service`

## Cut-over steps

1. [0079](../github-issues/0079-grit-meter-fail-closed.md): Make the grit meter fail closed and run once per user per day (Phase 3)
1. [Epic: Phase 6: gamification and notifications](../github-issues/epics/phase-6-gamification-and-notifications.md)

## Tests this module needs

- Rebuilt totals equal live totals.
- Month-boundary tests at 18:29 and 18:30 UTC, and the December → January roll.
- Board p95 ≤ 150 ms at 2× peak.
- `user.level_up` is never published for a decrease.

## Open questions

- When the grit meter moves from `scheduler-service` into this module.
