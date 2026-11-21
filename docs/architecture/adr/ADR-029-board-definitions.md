# ADR-029: Leaderboards as configurable board definitions

Status: Deferred (trigger: a second state is onboarded, or the national board launches)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: deferred; nothing is built.

## Context

Each chapter level will need its own boards, while the national board must stay comparable across
states. Today one state is live, so nothing needs configurable boards yet.

## Options considered

- **`board_definition` rows** declaring members, counted task levels, periods and visibility.
- **Hard-coded boards:** each new board needs a deploy.

## Decision

- **Deferred.** Until the trigger fires, the period totals carry `member_path` and
  `task_scope_path` from the start ([ADR-024](ADR-024-leaderboards-and-period-totals.md)), so nothing has to be rebuilt later.
- **When adopted:**
  - the national board counts only tasks with national scope;
  - state and district boards count global tasks plus their own level's tasks, configurable per
    definition;
  - fan-out per award stays bounded (at most 8 boards).

## Consequences

- No board-definition machinery to maintain before it is needed.

## Revisit when

- A second state is onboarded, or the national board launches.

## Related ADRs

[ADR-024](ADR-024-leaderboards-and-period-totals.md), [ADR-028](ADR-028-chapter-materialised-paths.md), [ADR-030](ADR-030-leaderboard-algorithms.md)
