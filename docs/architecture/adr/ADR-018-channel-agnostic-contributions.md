# ADR-018: A channel-agnostic contributions API with reconciliation

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. The Discord bot applies the karma rules itself and writes karma rows directly; there is no heartbeat and no reconciler.

## Context

Discord is today the only channel for submitting work, and the bot embeds the karma rules. A
nation-wide community includes learners who aren't on Discord. A channel driven only by
reactions can't be replayed after an outage, so awards can be lost with nothing to recover them
from. A liveness ping can look healthy while no events are being processed.

## Options considered

- **One contributions API for every channel,** plus reconciliation against the source of truth.
- **Keep channel-specific rules in each client:** rules diverge, and nothing can be replayed.

## Decision

- **One API.** `contributions` exposes one API for recording, approving and reversing
  submissions. Web, the mobile app, Discord (the bot as an API client) and partners are adapters
  that supply `source` and `source_ref`.
- **The heartbeat counts work done, not liveness.**
  - The bot reports how many task-channel events it processed each minute.
  - The alert fires when no task-channel events have been processed for 10 minutes while the
    channel shows activity.
- **A desired-state reconciler runs in the backend, independent of the bot.**
  - It runs every 15 minutes, with a read-only Discord credential.
  - It reads recent task-channel messages and their current reactions.
  - It computes each submission's desired state, then drives the same `contributions` commands
    the bot calls. The state machine ([ADR-004](ADR-004-karma-ledger.md)) makes this idempotent.
  - After an outage, its window widens to cover the gap.
- **An appraiser-queue age SLO** goes to community operations as a ticket, not a page.

## Consequences

- Adding a channel is an interface-layer change.
- The bot loses direct database access ([ADR-003](ADR-003-one-owner-per-table.md)).
- Missed events, toggles and removals during an outage all converge on the correct state.

## Revisit when

- A second submission channel (the app) goes live.

## Related ADRs

[ADR-003](ADR-003-one-owner-per-table.md), [ADR-004](ADR-004-karma-ledger.md), [ADR-033](ADR-033-slos-and-burn-rate-alerts.md), [ADR-046](ADR-046-tokens-keys-service-clients.md)
