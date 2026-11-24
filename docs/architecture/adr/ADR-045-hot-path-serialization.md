# ADR-045: Serialization on hot paths

Status: Accepted (new on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-21)
Implementation status at dev 7fd66060: not started. Serializers declare about 334 `SerializerMethodField`s against about 43 `prefetch_related` calls.

## Context

List endpoints serialize large pages through nested DRF serializers, and some run queries per row
inside method fields.

## Options considered

- **DRF serializers everywhere.**
- **`.values()` or dataclass selectors for lists, DRF for writes and details, and orjson only after
  measurement.**
- **msgspec with an orjson renderer everywhere:** a second schema system.

## Decision

- List selectors return `.values()` rows or slim dataclasses, mapped to camelCase by a light read
  serializer.
- An `orjson` renderer is adopted only if a benchmark of the 10 heaviest list endpoints shows that
  rendering takes at least 20% of p95. It is a new runtime dependency, so it needs architecture
  review.
- msgspec is rejected.

## Consequences

- Fewer queries per page, and predictable serialization cost.
- Read serializers stay simple.

## Revisit when

- The benchmark result is in.

## Related ADRs

[ADR-026](ADR-026-performance-budgets-in-ci.md), [ADR-044](ADR-044-api-standards-v1-2.md)
