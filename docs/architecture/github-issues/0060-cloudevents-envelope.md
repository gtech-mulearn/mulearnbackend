# Add IntegrationEvent with CloudEvents names and a payload test

| | |
|---|---|
| ID | 0060 |
| Phase / milestone | Phase 3: Schema safety net and events |
| Module | building_blocks |
| Size | M |
| Labels | arch, phase:3, module:building_blocks, type:feature, size:M |
| Depends on | 0059 |
| Blocks | 0061 |
| Repos | mulearnbackend |

## Why

Every event uses one envelope with CloudEvents attribute names, so any future consumer, in any language, can read it. Payloads must never carry personal data ([ADR-035](../adr/ADR-035-cloudevents-envelope.md), [05-events-and-background-work.md](../05-events-and-background-work.md#the-envelope)).

## Before you start

- Issue 0059 must be merged.

## What to do

1. Create `building_blocks/messaging/events.py` with a frozen dataclass base `IntegrationEvent`:
   - class attributes `EVENT_TYPE`, `VERSION` and `PRODUCER`, and instance fields `aggregate_type` and `aggregate_id`;
   - `to_envelope()` returns `specversion`, `id` (UUIDv7), `source` (`/mulearn/<PRODUCER>`), `type` (`org.mulearn.<EVENT_TYPE>.v<VERSION>`), `subject` (`<aggregate_type>:<aggregate_id>`), `time`, `datacontenttype`, `traceparent`, `correlationid` (the request id), `causationid` and `data` (the declared fields);
   - `parse_type(cloudevents_type: str) -> tuple[str, int]` turns `org.mulearn.contributions.submission_approved.v1` back into `("contributions.submission_approved", 1)`.
2. Add `publish(event: IntegrationEvent) -> None` to `building_blocks/messaging/outbox.py`. It calls `publish_raw` with `type=event.EVENT_TYPE`, the envelope's `source` and `subject`, and `envelope=event.to_envelope()`. Modules publish with `outbox.publish(event)` and never call `publish_raw` directly.
3. **One name for routing.** `OutboxEvent.type` and the consumer registry (issue 0062) both use the short `EVENT_TYPE`, such as `contributions.submission_approved`. The CloudEvents `type` appears only inside the envelope.
4. Create `tests/architecture/test_event_payloads.py`. For every `IntegrationEvent` subclass:
   - no field uses a reserved envelope name;
   - no field name looks personal (`email`, `phone`, `name`, `muid`, `address`, `dob`). The μCoin events' `muid` exception is on hold with that integration ([ADR-054](../adr/ADR-054-mucoin-external-consumer.md)), so the test allows none.
5. Add tests for the envelope fields and `parse_type`, and a MySQL-tier test in `building_blocks/tests/mysql/` that `outbox.publish` writes one row whose `type` is the short `EVENT_TYPE`.

## Acceptance criteria

- [ ] The envelope matches the example in 05-events-and-background-work.md.
- [ ] A test event with an `email` field fails the payload test.
- [ ] A test event with a `muid` field fails the payload test.

## How to test

```sh
scripts/test.sh building_blocks/tests/ tests/architecture/
scripts/test.sh --mysql building_blocks/tests/mysql/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Delivering events (issues 0061 and 0062).

## Notes for reviewers

The allowlist is a privacy decision. Check it can't grow without review.
