# Add the Discord bot heartbeat endpoint and metric

| | |
|---|---|
| ID | 0101 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | integrations |
| Size | S |
| Labels | arch, phase:4, module:integrations, type:feature, size:S, core-review |
| Depends on | 0023, 0090 |
| Blocks | 0102 |
| Repos | mulearnbackend |

## Why

If the Discord bot stops recording karma, nothing notices today: it can go on for days. A heartbeat that counts processed events, not just liveness, catches that within minutes ([ADR-018](../adr/ADR-018-channel-agnostic-contributions.md)).

## Before you start

- Issue 0090 must be merged.
- Issue 0023 must also be merged.

## What to do

1. Create the `integrations` module as [Create a module](../16-contributing-to-the-architecture.md#create-a-module) describes. It starts without tables.
2. Add `POST /api/v1/internal/integrations/heartbeat/`, an `InternalAPIView` with scope `integrations.heartbeat`. The body is `{"processed": int, "channelActivity": int, "windowSeconds": 60}`. It stores the latest heartbeat per client on the `state` cache, and exports the metrics `bot_events_processed` and `bot_channel_activity`.
3. Add a selector `last_heartbeat(client)`.
4. Document the alert rule for the dashboards: no processed events for 10 minutes while the channel shows activity.
5. Add tests.

## Acceptance criteria

- [ ] A heartbeat is stored and exported as metrics.
- [ ] The endpoint needs the service scope.

## How to test

```sh
scripts/test.sh modules/integrations/tests/
```

## Out of scope

- The bot side (issue 0102).
- The alert itself (configured by a maintainer with the dashboards).

## Notes for reviewers

Check that it counts processed events, not process liveness.
