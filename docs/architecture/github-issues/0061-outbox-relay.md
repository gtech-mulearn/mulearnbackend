# Add the outbox relay

| | |
|---|---|
| ID | 0061 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | L |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:L, core-review |
| Depends on | 0004, 0037, 0059, 0060, 0064 |
| Blocks | 0062, 0078, 0105 |
| Repos | mulearnbackend |

## Why

Committed outbox rows must reach the broker, at least once, without holding row locks while sending ([ADR-005](../adr/ADR-005-transactional-outbox.md)).

## Before you start

- Issues 0059 and 0060 must be merged.
- Issues 0004, 0037 and 0064 must also be merged.

## What to do

1. Create `building_blocks/messaging/relay.py` with `relay_once(batch=200) -> int`. It runs three steps:
   1. **claim:** in one transaction, `SELECT … FOR UPDATE SKIP LOCKED` the due rows (`published_at IS NULL`, and `claimed_until` null or in the past), ordered by `id`, set `claimed_until = now + 60 s`, and commit;
   2. **send:** send each envelope to the broker, outside any transaction, as a Celery task `building_blocks.messaging.dispatch` on the queue mapped for its type (default `default`);
   3. **mark:** set `published_at` on the rows that were sent.
2. Create `building_blocks/management/commands/outbox_relay.py`. It loops `relay_once`, sleeps 1 s when idle, stops cleanly on SIGTERM, and records the outbox lag as a metric.
3. Add the `relay` service to `docker-compose.local.yml`, and the `relay` role to `deploy/compose.yml` (issue 0037), on every node as [10-infrastructure-and-deployment.md](../10-infrastructure-and-deployment.md) lists. `SKIP LOCKED` makes several relays safe. In the same file, replace the single `worker` role with the worker groups from that page (`worker-fast`, `worker-notify` and `worker-bulk`), using the queues from issue 0064.
4. Add MySQL-tier tests:
   - two relays running at once never send the same row twice;
   - a send failure leaves the row to be retried after its claim expires;
   - rows are marked only after sending.

## Acceptance criteria

- [ ] The concurrency test passes with two relays.
- [ ] Stopping the relay mid-batch loses nothing: the rows are re-sent later.
- [ ] No row lock is held during the send step (show this with a test that blocks the send).

## How to test

```sh
scripts/test.sh --mysql building_blocks/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Consumers (issue 0062).
- Running the relay in deployed environments (issue 0078 for staging, issue 0105 for production).

## Notes for reviewers

Check the claim/send/mark order and the `SKIP LOCKED` query. This is core infrastructure.
