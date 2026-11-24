# ADR-001: Domain-oriented modular monolith

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Business code still lives in `api/`, `db/`, `utils/` and `mu_celery/`.

## Context

The backend is one Django codebase with several hundred routes. Many packages read and write the
same tables, and rules are spread across views, serializers and helpers. The team is small and
largely volunteer, and contributors range from first-timers to maintainers.

## Options considered

- **A modular monolith:** one deployable, bounded-context modules, boundaries enforced in CI.
- **Microservices:** independent deploys, but network calls replace joins on the karma path, and
  the operating cost is beyond a volunteer team.
- **An event-driven or CQRS-first system:** more moving parts than today's load needs.
- **A rewrite:** high risk and long, and it delivers nothing until it is finished.

A weighted decision matrix scored the modular monolith highest on scalability, reliability,
complexity, contributor friendliness, operating cost and migration cost.

## Decision

- Keep one deployable.
- Organise new code into bounded-context modules under `modules/`, each with the same layered
  structure ([ADR-017](ADR-017-one-layered-module-structure.md)).
- A module exposes one public surface, `public.py` and `contracts.py`.
- Boundaries are enforced by automation ([ADR-016](ADR-016-architecture-enforced-by-automation.md)).

**Extracting a module into its own service** is considered only when all five of these hold:
1. It needs an independent release cadence or scaling profile that the monolith cannot give.
2. It owns all of its tables, and no other writer exists.
3. Its cross-module traffic is already events or `public.py` calls.
4. A team can own its on-call.
5. The extraction cost has been estimated and accepted in an ADR.

## Consequences

- Low infrastructure cost, and one codebase to learn.
- Ownership of data and rules becomes explicit.
- The structure holds only with discipline, so CI checks enforce it.
- Legacy packages stay in place and shrink as their behaviour moves into modules.

## Revisit when

- A module meets all five extraction conditions.

## Related ADRs

[ADR-016](ADR-016-architecture-enforced-by-automation.md), [ADR-017](ADR-017-one-layered-module-structure.md), [ADR-038](ADR-038-modules-own-their-tables.md)
