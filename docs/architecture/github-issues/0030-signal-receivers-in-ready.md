# Register signal receivers in AppConfig.ready()

| | |
|---|---|
| ID | 0030 |
| Phase / milestone | Phase 2: Serving and runtime |
| Module | platform |
| Size | M |
| Labels | arch, phase:2, module:platform, type:chore, size:M |
| Depends on | 0011 |
| Blocks | 0031 |
| Repos | mulearnbackend |

## Why

Several signal receivers in `api/common/common_consumer.py` (`db_signals`, `handle_org_link_cache`, `handle_ig_link_cache`, `handle_session_cache` and the karma-log receiver) are registered only because the WebSocket routing (`api/routing.py` → `api/common/routing.py`) imports that module.

As a result, they never fire in Celery workers, and they will stop firing everywhere once Channels is retired (issue 0034). Some of them invalidate mentor-dashboard caches, so missed invalidations mean stale dashboards ([ADR-039](../adr/ADR-039-retire-channels-and-daphne.md)).

## Before you start

- Issue 0011 (CI) must be merged.
- Read `api/common/common_consumer.py` from the line `channel_layer = get_channel_layer()` to the end, and `api/apps.py`.

## What to do

1. Create `api/common/signals.py` and move into it every `@receiver` function from `api/common/common_consumer.py`, plus `invalidate_scope_cache`, unchanged. Leave the WebSocket consumer class where it is.
2. In `db_signals` / `_broadcast_landing_stats`, keep the WebSocket broadcast for now, but import the channel layer lazily inside the function, so `signals.py` doesn't import Channels at module level.
3. In `api/apps.py`, add `ready()` to `ApiConfig`, importing `api.common.signals`.
4. Remove the receivers from `common_consumer.py`. It now imports `landing_stats` from wherever it lives today, and nothing else changes.
5. Add `api/common/tests/test_signal_registration.py`. Without importing any routing module, it asserts that each receiver is connected to `post_save` and `post_delete` for its models, using `post_save.has_listeners(...)` and the receiver list.

## Acceptance criteria

- [ ] The receivers are registered in a process that never imports `api/routing.py`.
- [ ] Every receiver is registered exactly once (no double registration in the ASGI process).
- [ ] Release notes name the behaviour change: the cache invalidations now also run for writes made in workers.

## How to test

```sh
scripts/test.sh api/common/tests/test_signal_registration.py
```

## Out of scope

- Removing the WebSocket broadcast (issue 0034).
- Changing what any receiver does.

## Notes for reviewers

Check for double registration: a receiver connected twice runs twice.
