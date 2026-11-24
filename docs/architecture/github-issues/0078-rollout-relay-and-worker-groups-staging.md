# Run the relay and the worker groups on staging

| | |
|---|---|
| ID | 0078 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | S |
| Labels | arch, phase:3, module:platform, type:chore, size:S, maintainer-only |
| Depends on | 0037, 0061, 0064, 0072 |
| Blocks | 0105 |
| Repos | mulearnbackend |

## Why

The outbox drains only where the relay runs, and tasks run on their routed queues only where the worker groups run (issues 0061 and 0064). Running both on staging first, and checking that events flow and duplicates are skipped, makes the production rollout (issue 0105) routine ([10-infrastructure-and-deployment.md](../10-infrastructure-and-deployment.md)).

## Before you start

- Maintainer-only: it changes staging.
- Issues 0037, 0061, 0064 and 0072 must be merged.

## What to do

1. Deploy the relay and the worker groups to staging with `scripts/deploy.sh staging <digest>` (issues 0037, 0061 and 0064). Exactly one node runs beat.
2. Confirm `outbox_relay` is running and the outbox lag metric stays near zero.
3. From a shell on staging, publish a test event, with test data, for an event type that has a registered consumer. Confirm the consumer records it once in the inbox (issue 0062).
4. Re-deliver the same event id, and confirm the consumer skips it as a duplicate.
5. Watch the dead letters and the queue depths for 24 hours, and record the counts on the issue.

## Acceptance criteria

- [ ] The outbox lag stays near zero on staging for 24 hours.
- [ ] A test event is consumed exactly once, and its re-delivery is skipped.
- [ ] Beat runs on exactly one staging node.
- [ ] No dead letters come from the relay or the consumers in that time.

## How to test

Record the commands, the test event id and the counts on the issue.

## Out of scope

- Production (issue 0105).
- Webhooks to external consumers (on hold with the μCoin integration, [ADR-054](../adr/ADR-054-mucoin-external-consumer.md)).

## Notes for reviewers

Use test data only, so nothing real reacts to the test event.
