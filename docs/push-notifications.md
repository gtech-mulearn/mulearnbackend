# Push notifications (FCM)

The mobile app gets real push notifications. They come from three sources, and all three go through one sender that decides whether to send and paces itself:

1. **Activity**: an existing in-app notification (a circle join approved, karma awarded, a job application status) also goes out as a push when its type allows push.
2. **Engagement**: a scheduled engine that looks at what each learner did or stopped doing and sends at most one nudge a day to bring them back.
3. **Admin campaigns**: pushes an admin writes, targets and schedules from the dashboard.

## Why this shape

- In-app notifications already work (`api/notification/service.py`): deduplication, broadcast rows for big audiences, writes deferred until the business transaction commits. Push reuses that pipeline instead of building a second one. The templates already reserved a `PUSH` channel.
- Celery and Redis are already deployed. Every send runs in a worker, never inside a web request.
- The server must not be overloaded:
  - sends are batched (500 tokens per FCM call) and rate-capped globally;
  - the engine spreads learners across the day;
  - an admin kill switch stops all sending at once.
- A failed push never affects the in-app notification it came from: the push is queued after the in-app rows are written, and any error is only logged.

## Data (db-scripts `alter-1.93.sql` + `alter-1.94.sql`)

`alter-1.93.sql` creates the tables below. `alter-1.94.sql` adds `push_delivery_log.variant` and appends the ten notification and push action types (`NOTIF_*`, `PUSH_*`) to `system_action_log.action_type`, which the activity log needs.

| Table | Purpose |
|---|---|
| `user_push_device` | One row per FCM token. Columns: user, platform, app version, time zone, `is_active`, `last_seen_at` (app opens, throttled to one update per hour), failure count. A token moves to whoever registers it last, so a shared phone never pushes to the previous account. |
| `user_push_preference` | Per user. Columns: push on/off, nudges on/off, muted categories, quiet hours (local), time zone. If a user has no row, the defaults apply. |
| `push_delivery_log` | One row per decision: sent, failed, or skipped (with the reason). Also `opened_at`, reported by the app, and `variant`, the copy version that was sent (see Copy versions). Caps, cooldowns, fatigue and admin stats are computed from it. Rows older than 90 days are purged daily. Unique on (user, dedupe_key), so retries never double-send. |
| `push_campaign` | Admin pushes: title, body, deep link, audience, schedule, status and counters. |
| `push_config` | Admin-tunable settings as JSON per key: `global` plus one per engagement rule. The code holds the defaults; a stored row overrides only the keys it sets. |

## Sending policy (`api/push/policy.py`, pure functions)

These checks run in order. The first one that fails decides, and it is logged as `skipped_<reason>`:

1. `kill_switch` (global)
2. User has push off, or the category is muted (`skipped_pref`). Engagement also needs nudges on.
3. No active device (`no_device`).
4. Quiet hours in the user's time zone (default 22:00–08:00). Activity pushes are **deferred** to the end of the quiet window. Engagement and campaigns are skipped, or deferred when the campaign says so.
5. Daily caps per user over a rolling 24 hours (one query covers every recipient whatever their time zone): `daily_cap` across all pushes (default 6); `engagement_daily_cap` (default 1).
6. Per-rule cooldown, multiplied by fatigue: each unopened engagement push in the last 14 days doubles the cooldown, up to 14 days. One open resets it.

## Load control

- **Global rate:** a token bucket in Redis (`push_config.global.max_per_minute`, default 6000). A worker that finds the bucket empty reschedules its chunk with a countdown instead of spinning.
- **FCM calls:** `send_each_for_multicast` with up to 500 tokens per call. Tokens FCM reports as unregistered or invalid are deactivated at once.
- **Big audiences** (campaigns, broadcast-scale notifications) fan out in chunks of 1000 users using keyset pagination over device rows. Each chunk is its own Celery task, so no task loads the whole user base.
- **Engagement cohorts:** each learner has a stable nudge hour, `crc32(user_id) % window`, inside their local 10:00–20:00 window. The hourly run only considers learners whose nudge hour is now, which is about a tenth of active learners per run. Time-critical rules (a meeting or event starting soon) ignore the slot but still respect quiet hours and caps.
- **Device registration** is an upsert. The app calls it once per launch and when FCM rotates the token; `last_seen_at` is written at most once an hour.

## Engagement rules (`api/push/engine.py`)

Each rule produces candidates with a set-based query over the cohort; there are no per-user queries. Each learner then gets their single highest-scoring candidate. The score is the rule weight × urgency, minus fatigue.

| Rule | Trigger | Weight | Default cooldown |
|---|---|---|---|
| `MEETING_SOON` | A meeting of the learner's circle starts in the next 60–120 min | 100 | per meeting |
| `EVENT_SOON` | An event the learner marked interested starts in the next 24 h | 80 | per event |
| `STREAK_RESCUE` | Karma on each of the last ≥2 days, none today; local time 18:00–20:00 | 70 | 1 day |
| `COMEBACK` | No app open for 3 / 7 / 14 / 30 days (one push per tier per absence). Hook: new tasks in the learner's interest groups since they left | 50 | per tier |

Each rule's on/off switch, thresholds, cooldown and copy can be edited in `push_config` from the dashboard.

## API (`/api/v1/push/`)

| Method | Path | Who | What |
|---|---|---|---|
| POST | `devices/` | signed in | Register or refresh a token: `{token, platform, app_version, timezone}` |
| DELETE | `devices/` | signed in | Unregister on sign-out: `{token}` |
| POST | `opened/` | signed in | `{dedupe_key}`. Marks the caller's push opened (feeds the fatigue check) |
| GET/PATCH | `preferences/` | signed in | Push and nudges switches, muted categories, quiet hours |
| GET/PATCH | `admin/config/` | Admins only (settings changes) | Kill switch, caps, rate, quiet-hour defaults, per-rule settings, push on/off per notification type |
| GET/POST | `admin/campaigns/` | verified Admin, Fellow, Associate | List / create (draft or scheduled) |
| POST | `admin/campaigns/<id>/send/`, `.../cancel/` | verified Admin, Fellow, Associate | Send now / cancel |
| POST | `admin/test/` | verified Admin, Fellow, Associate | Send a test push to the admin's own devices |
| GET | `admin/stats/` | verified Admin, Fellow, Associate | Last 14 days (`?days=`, up to 90): sent, skipped by reason, opened, per source and rule, plus `variants`: sent and opened per copy version |

Who can use the admin endpoints: everything under `admin/` is for verified Admins, Fellows and Associates, checked against the database (a token that says Fellow but has no verified Fellow link is refused). The one exception is `admin/config/`, where changing settings is Admin-only; reading it is open to the team. Every change an admin makes (campaigns, test sends, settings) is written to the activity log, which the team reads at `GET /api/v1/notification/activity-log/` (filters: `action`, `actor`, `from`, `to`; paginated, newest first, ties broken by id). An announcement edit that re-sends identical values is saved but not logged.

### Activity log items

Each row is a `system_action_log` row. The writer (`api/notification/audit.py`, `record`) stores the team details under `new_data._audit`: `roles`, `audience_size`, `audience_label` and `title`, the subject's name (the campaign or announcement title, the title being sent, or the test push title; for an edit, the title before the change; `null` for delete-all and settings changes). Each item in the response has:

| Field | What |
|---|---|
| `id`, `action`, `label` | Row id, action type, human label ("Sent push campaign") |
| `actor` | `{full_name, muid}` |
| `roles` | The actor's verified team roles at the time |
| `title` | `new_data.title`, else `old_data.title`, else `_audit.title`. Delete-all shows "N announcements", settings changes show "Push settings" |
| `entity_name`, `entity_id` | What the row is about: `broadcast_notification` (an id, or `all`), `notification` (send to everyone written as personal rows), `push_campaign`, `push_test` (the actor's id) or `push_config` (`config`) |
| `campaign` | For `push_campaign` rows, the campaign's live `{status, target_count, sent_count, skipped_count, failed_count}`, read from `push_campaign` in one query per page, because the counts keep changing after the send is logged. `null` for other rows and for a campaign that no longer exists |
| `audience_size`, `audience_label` | Head count (campaigns: `target_count`; send to everyone: the recipient count) or a label |
| `created_at` | ISO time |
| `old_data`, `new_data` | What changed, for a details view (`new_data` without `_audit`) |

## Copy versions

Both nudges and activity pushes carry several versions of their text, so people do not see the same wording every time. A version is `{key, title, body}`: the key is `^[a-z0-9_]{1,16}$` and unique within its rule or type, the title is at most 40 characters and the body at most 100, and a rule has 1 to 10 versions. Each push records the version it used as `push_delivery_log.variant`, `"<RULE_OR_TYPE>:<key>"` (at most 40 characters), so the format is the same for both.

- **Nudges** (`api/push/engine.py`): versions live in the rule's settings. Rotation is per person, over the nudges of that rule the person was sent in the last 35 days (`engine.ROTATION_LOOKBACK_DAYS`, separate from `fatigue_lookback_days`): a version they had in their last `len-1` of those is skipped, so within that window every version is seen before any repeats. 35 days covers five weekly meeting nudges and all four comeback tiers of one absence (days 3, 7, 14 and 30). A version last sent more than 35 days ago can come up again. An old copy override that has only a title or body keeps the default version's other half.
- **Activity pushes** (`api/notification/templates.py`): the `(TYPE, "PUSH")` templates for karma awarded, learning-circle join approved, rejected, invite and meeting scheduled, event cancelled and job application status each hold three versions. One is picked at random per send (no history is kept), and `variant` is passed through `send_activity_push` to the sender. If a version cannot be filled from the producer's context, the push falls back to the in-app text with no variant.
- **Stats**: `admin/stats/` returns `variants: [{variant, sent, opened}]`, counted over `status="sent"` rows with a variant in the same window, ordered by `variant`. Open rate per version is `opened / sent`.

## Scheduling (Celery beat)

| Task | When |
|---|---|
| `run_engagement` | Hourly at :05 |
| `dispatch_due_campaigns` | Every minute (scheduled campaigns) |
| `purge_push_logs` | Daily |

`docker-compose` gains a `celery-beat` service. Until now, no beat scheduler process was defined, so `CELERY_BEAT_SCHEDULE` entries only ran where something else ran beat.

## Deploying

Deploy the Celery workers together with the web servers, or before them. New code enqueues `send_activity_push` with a `variant=` keyword. A worker still on the old code does not accept it, so the task fails and that push is lost. Workers on the new code accept enqueues from old web servers too, because `variant` defaults to `None`.

## Configuration (environment)

- `FIREBASE_CREDENTIALS`: path to the Firebase service-account JSON, or the JSON itself. If it is empty, push is disabled: everything is logged as `skipped_disabled` and nothing breaks.
- `PUSH_ENABLED` (default `True`): a deploy-time master switch on top of the admin kill switch.

## Not in this change

Email and WebSocket channels; FCM topic subscriptions (per-user caps and quiet hours need per-device sends); iOS APNs setup (comes with the iOS flavor).
