# Serve landing statistics over cached HTTP

| | |
|---|---|
| ID | 0031 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:feature, size:M |
| Depends on | 0030 |
| Blocks | 0034 |
| Repos | mulearnbackend |

## Why

Landing-page statistics are pushed over a WebSocket (`/ws/.../public/landing-stats/`), but no first-party client opens a WebSocket. Serving them from a cached HTTP endpoint lets Channels be retired without losing the feature.

## Before you start

- Issue 0030 must be merged.
- Read `api/common/common_consumer.py` (the `GlobalCount` consumer and `landing_stats`) and `api/common/urls.py`.

## What to do

1. Add a view `LandingStatsAPI` in `api/common/common_views.py`. It returns the same data `landing_stats.data` holds today, in the standard envelope.
2. Route it at `path("landing-stats/", ...)` in `api/common/urls.py`, which serves `/api/v1/public/landing-stats/`.
3. Cache the result for 60 seconds under a versioned key, and send `Cache-Control: public, max-age=60`.
4. In `signals.py` (created in `api/common/` by issue 0030), make `db_signals` invalidate that cache key on commit, alongside the existing broadcast.
5. Add tests: the response shape matches today's WebSocket payload fields, and a second call within 60 s doesn't recompute.

## Acceptance criteria

- [ ] `GET /api/v1/public/landing-stats/` returns the statistics without authentication.
- [ ] The fields match what the WebSocket sent.
- [ ] A user save invalidates the cached value after commit.

## How to test

```sh
scripts/test.sh api/common/tests/
```

## Out of scope

- Removing the WebSocket (issue 0034).
- Changing which statistics are shown.

## Notes for reviewers

Check the cache headers: this endpoint is public, and the statistics are not personal.
