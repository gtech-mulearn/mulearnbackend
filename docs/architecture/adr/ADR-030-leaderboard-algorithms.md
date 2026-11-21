# ADR-030: Leaderboard algorithms: packed scores, exact top-K, approximate long-tail ranks

Status: Deferred (trigger: any board passes 1 million members)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: deferred; nothing is built.

## Context

Very large boards need deterministic order for equal scores, and an instant "my rank" for
everyone. Nothing at today's scale needs these algorithms.

## Options considered

- **Packed scores in sorted sets, an exact top-K, and histogram ranks for the long tail.**
- **Exact ranks for everyone:** memory and CPU grow with board size.

## Decision

- **Deferred.**
- **When adopted:**
  - sorted-set scores pack karma with a time tiebreak, updated atomically;
  - boards over 2 million members keep an exact top 100,000;
  - long-tail ranks come from a Fenwick-tree score histogram, shown as percentiles;
  - everything is rebuildable from the ledger.

## Consequences

- No extra state or memory budget until the trigger.

## Revisit when

- Any board passes 1 million members.

## Related ADRs

[ADR-024](ADR-024-leaderboards-and-period-totals.md), [ADR-029](ADR-029-board-definitions.md), [ADR-043](ADR-043-redis-cache-and-state.md)
