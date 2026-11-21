# ADR-028: A chapter hierarchy with materialised paths

Status: Accepted
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Organisations have no chapter hierarchy.

## Context

A national rollout federates μLearn into state, district and campus chapters, each with its own
membership, tasks and leads.

## Options considered

- **An `org_chapter` tree with materialised paths.**
- **A closure table:** more flexible, but heavier writes, and the depth is at most 4.
- **Separate deployments or databases per state:** high cost, and they break national features.

## Decision

- An `org_chapter` tree stores a materialised `path`, for example `IN/KL/EKM/…`. (The name
  `chapter` already belongs to the comics tables.) It is owned by `organizations`.
- Users, tasks, grants and ledger entries carry paths.
  - Ancestry is resolved by splitting the path.
  - Subtrees are found by an indexed prefix.
- Paths are frozen into ledger entries at award time.
- Path columns use the `ascii_bin` collation ([ADR-015](ADR-015-uuid-keys-and-public-ids.md)).

## Consequences

- Isolation is enforced by scope, and a new state is configuration.
- The path is ready to be a future partition key.

## Revisit when

- The hierarchy needs more than four levels, or chapters need to move between parents often.

## Related ADRs

[ADR-007](ADR-007-scoped-grants-and-policies.md), [ADR-015](ADR-015-uuid-keys-and-public-ids.md), [ADR-024](ADR-024-leaderboards-and-period-totals.md), [ADR-029](ADR-029-board-definitions.md)
