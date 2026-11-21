# Phase 6: gamification and notifications

| | |
|---|---|
| Epic | phase-6-gamification-and-notifications |
| Phase / milestone | Phase 6: Gamification and notifications |
| Labels | arch, phase:6, type:epic |

## What it will contain

From [09-performance-and-caching.md](../../09-performance-and-caching.md), [ADR-024](../../adr/ADR-024-leaderboards-and-period-totals.md), [ADR-047](../../adr/ADR-047-notification-pipeline.md) and [ADR-054](../../adr/ADR-054-mucoin-external-consumer.md):

- **The `gamification` module.**
  - It owns the level and achievement tables.
  - It adds `karma_period_total`, fed by batched ledger-event consumers, with `rebuild_period_totals`.
  - Leaderboard readers switch to period totals behind a flag, after a published diff. Monthly boards use IST month bounds.
- **Level writes move into `gamification`:**
  - signup creates level progress from `UserRegistered`;
  - the bot's level writes end with its move to the API;
  - the scheduler's grit meter is absorbed into a backend job.
- **`user.level_up` for `mucoin-service`** (on hold with the μCoin integration). When it resumes, it is published by `gamification` on every level increase and never on a decrease. It can only be published once `gamification` owns every level write, because today the bot and the scheduler change levels directly in MySQL.
- **The `notifications` module:**
  - in-app, push and email delivery through the outbox, with claim-first de-duplication;
  - quiet hours as due rows, not long Celery ETAs;
  - email off the request path, so no SMTP runs inside a request.

## Entry conditions

- The Phase 4 cut-over epic is finished, so the ledger is the source of truth.
- The consumers from Phase 3 (issue 0062) are in production.

## Exit criteria

- Board p95 is at most 150 ms at 2× peak.
- Rebuilt and live period totals agree with zero difference.
- No request path scans karma rows for a board.
- `user.level_up` deliveries match level increases one to one over 14 days.
- No SMTP call runs on a request path; a fitness function checks this.
