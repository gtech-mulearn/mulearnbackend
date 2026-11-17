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

## Data (db-scripts `alter-1.93.sql`)

| Table | Purpose |
|---|---|
| `user_push_device` | One row per FCM token. Columns: user, platform, app version, time zone, `is_active`, `last_seen_at` (app opens, throttled to one update per hour), failure count. A token moves to whoever registers it last, so a shared phone never pushes to the previous account. |
| `user_push_preference` | Per user. Columns: push on/off, nudges on/off, muted categories, quiet hours (local), time zone. If a user has no row, the defaults apply. |
| `push_delivery_log` | One row per decision: sent, failed, or skipped (with the reason). Also `opened_at`, reported by the app. Caps, cooldowns, fatigue and admin stats are computed from it. Rows older than 90 days are purged daily. Unique on (user, dedupe_key), so retries never double-send. |
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
| POST | `opened/` | signed in | `{delivery_id}`. Marks a push opened (feeds the fatigue check) |
| GET/PATCH | `preferences/` | signed in | Push and nudges switches, muted categories, quiet hours |
| GET/PATCH | `admin/config/` | Admins | Kill switch, caps, rate, quiet-hour defaults, per-rule settings, push on/off per notification type |
| GET/POST | `admin/campaigns/` | Admins | List / create (draft or scheduled) |
| POST | `admin/campaigns/<id>/send/`, `.../cancel/` | Admins | Send now / cancel |
| POST | `admin/test/` | Admins | Send a test push to the admin's own devices |
| GET | `admin/stats/` | Admins | Last 14 days: sent, skipped by reason, opened, per source and rule |

## Scheduling (Celery beat)

| Task | When |
|---|---|
| `run_engagement` | Hourly at :05 |
| `dispatch_due_campaigns` | Every minute (scheduled campaigns) |
| `purge_push_logs` | Daily |

`docker-compose` gains a `celery-beat` service. Until now, no beat scheduler process was defined, so `CELERY_BEAT_SCHEDULE` entries only ran where something else ran beat.

## Configuration (environment)

- `FIREBASE_CREDENTIALS`: path to the Firebase service-account JSON, or the JSON itself. If it is empty, push is disabled: everything is logged as `skipped_disabled` and nothing breaks.
- `PUSH_ENABLED` (default `True`): a deploy-time master switch on top of the admin kill switch.

## Not in this change

Email and WebSocket channels; FCM topic subscriptions (per-user caps and quiet hours need per-device sends); iOS APNs setup (comes with the iOS flavor).
