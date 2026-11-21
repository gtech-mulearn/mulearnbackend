# ADR-026: Performance budgets are CI gates

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. No test enforces query counts or payload sizes.

## Context

Without budgets, N+1 queries and payload bloat return silently.

## Options considered

- **Query-count and payload budgets in CI, per endpoint class.**
- **Monitoring only:** regressions are found in production.

## Decision

- New and moved endpoints carry query-count tests (`django_assert_max_num_queries`) at page size 1
  and at the maximum page size. The query count must not grow with page size.
- Legacy endpoints join the budgets when they move into a module.
- Exceptions need the module owner plus an architecture maintainer.

## Consequences

- A little more test code per endpoint.
- Regressions are caught at pull-request time.

## Revisit when

- A budget is routinely exceeded with sign-off (revise the budget class).

## Related ADRs

[ADR-016](ADR-016-architecture-enforced-by-automation.md), [ADR-045](ADR-045-hot-path-serialization.md)
