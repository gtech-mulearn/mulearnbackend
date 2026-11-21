# ADR-035: CloudEvents 1.0 attribute names for integration events

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. There is no event envelope yet.

## Context

Events will cross modules, and they already need to leave the backend for `mucoin-service`
([ADR-054](ADR-054-mucoin-external-consumer.md)). A standard envelope avoids a bespoke format. The outbox
envelope ([ADR-005](ADR-005-transactional-outbox.md)) carries a UUIDv7 id, a version and `traceparent`.

## Options considered

- **CloudEvents attribute names on the outbox envelope.**
- **A bespoke envelope:** every future consumer has to learn it.

## Decision

The envelope uses CloudEvents attribute names:
- `id`: a UUIDv7;
- `source`: `/mulearn/<module>`;
- `type`: `org.mulearn.<module>.<event>.v<N>`;
- `specversion`, `time` and `datacontenttype`;
- `subject`: the aggregate id;
- extensions: `traceparent`, `correlationid` and `causationid`.

Headers are stored as snake_case JSON. Payload schemas live in each module's `contracts.py` and
stay language-neutral.

## Consequences

- Brokers, change-data capture and consumers in other languages can interoperate later without
  re-encoding.

## Revisit when

- The first external event consumer arrives.

## Related ADRs

[ADR-005](ADR-005-transactional-outbox.md)
