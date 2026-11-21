# ADR-005: Transactional outbox relayed to Celery on Redis

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Follow-up work runs inline in request code or through `.delay()` calls on one default Celery queue.

## Context

Side effects such as emails, Discord roles, notifications and cross-module reactions run inline or
fire-and-forget. When one failed, state and side effect fell out of step. Celery on
Redis is already deployed.

## Options considered

- **An outbox table written in the business transaction,** relayed to Celery.
- **Publishing directly to the broker after commit:** an event is lost if the process dies
  between commit and publish.
- **A new broker** (RabbitMQ, Kafka, SQS): more infrastructure than current event volume
  justifies.

## Decision

- Services publish integration events with `building_blocks.messaging.outbox.publish` inside
  `transaction.atomic()`.
- **The relay claims, sends, then marks:**
  1. It claims a batch of rows (`claimed_until`) and commits.
  2. It sends the batch to the broker outside any row lock.
  3. It marks the rows published.
- **Consumers are idempotent.**
  - An inbox records `(consumer, event_id)`, so a redelivery is a no-op.
  - After the last retry, a delivery is parked as a dead letter, and `replay_dead_letters`
    re-sends it.
- **Routing is by event `type`, and tolerates versions.** A consumer declares which versions it
  accepts. An unknown version goes to a dead letter and raises an alert; it is never silently
  dropped.
- **Ordering per aggregate is deferred.** `relay_partition` is a generated column on the outbox
  table, so no writer sets it and turning ordering on later needs no backfill.
- Retention: published outbox rows 30 days; inbox rows 30 days, never shorter than the window in
  which a dead letter may be replayed.

### Refinements (2026-11-21)

- The outbox table ships with its claim columns and its generated partition column in one expand alter, so no later backfill is needed.
- The same outbox also carries integration events for services outside the backend. A webhook delivery adapter signs and posts them to external consumers such as `mucoin-service` ([ADR-054](ADR-054-mucoin-external-consumer.md)).
- One relay runs per node. Claim, send, mark with `SKIP LOCKED` makes that safe and gives failover.
- An event type with no subscriber yet is only counted. An event whose subscribers exist but none accepts its version goes to a dead letter and raises an alert.

## Consequences

- At-least-once delivery, with each effect applied once.
- State and its events can't disagree.
- A small operational surface: the relay, housekeeping and queue monitoring.
- Consumers must tolerate duplicates and out-of-order delivery until ordering is enabled.

## Revisit when

- A consumer appears that can't tolerate reordering (enable partitioned relay loops).
- Event volume exceeds about 5,000 per second, or a replay window beyond 7 days is needed
  (consider Redis Streams or binlog change-data capture).

## Related ADRs

[ADR-035](ADR-035-cloudevents-envelope.md), [ADR-041](ADR-041-transactions-and-consistency.md), [ADR-042](ADR-042-background-work-celery.md), [ADR-054](ADR-054-mucoin-external-consumer.md)
