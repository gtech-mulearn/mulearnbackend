# Run the relay and the worker groups in production

| | |
|---|---|
| ID | 0105 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | platform |
| Size | S |
| Labels | arch, phase:3, module:platform, type:chore, size:S, maintainer-only |
| Depends on | 0047, 0061, 0064, 0078 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

The outbox drains only where the relay runs, and routed tasks run only where their worker groups run. Until both run in production, published events wait in the outbox and nothing consumes them ([10-infrastructure-and-deployment.md](../10-infrastructure-and-deployment.md)).

## Before you start

- Maintainer-only: it changes production.
- Issue 0078 (the staging rollout) must have passed.
- Issues 0047, 0061 and 0064 must also be merged.

## What to do

1. Add the `relay` role and the worker groups to `deploy/production/nodes.txt`. Exactly one node runs beat.
2. Deploy with `scripts/deploy.sh production <digest>`, canary first.
3. Watch the outbox lag, the dead letters and the queue depths for 24 hours.
4. Record the counts and the first consumed event id on the issue.

## Acceptance criteria

- [ ] Outbox lag p95 stays under 10 s for 24 hours.
- [ ] No dead letters come from the relay or the consumers in that time.
- [ ] The first event published after the deploy is consumed, and its id is recorded.
- [ ] Beat still runs on exactly one node.

## How to test

Paste the deploy log and the 24-hour metric summaries on the issue.

## Out of scope

- New queues or roles.
- Turning on further integration consumers.

## Notes for reviewers

Check the rollback: removing the roles from `nodes.txt` and redeploying stops delivery, and the rows wait safely in the outbox.
