# ADR-034: Contribution integrity

Status: Accepted in part (synchronous guards accepted; asynchronous detectors deferred)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. The Discord bot applies its own guards; the backend has none of these.

## Context

National karma creates incentives to game the system: duplicate proofs, scripted submissions and
collusive approvals.

## Options considered

- **Synchronous guards now; asynchronous detectors on a trigger.**
- **The full detector pipeline now:** needs a staffed review queue and tuning data that doesn't
  exist yet.

## Decision

- **Synchronous guards** run in `contributions` services:
  - idempotency;
  - cooldowns;
  - usage limits, as lifetime caps per the product ruling;
  - no self-approval.
- **Deferred asynchronous detectors:**
  - perceptual hashes for images;
  - MinHash for text;
  - velocity checks;
  - approval-graph collusion analysis.
- **When adopted,** detector actions are hold, review, or reverse through the ledger. The
  pipeline is tuned for precision, and every action is audited.

## Consequences

- The synchronous guards stop the common cases. Sophisticated abuse is caught by review until the detectors
  exist.

## Revisit when

- The national board launches, or reported abuse exceeds 1% of awards in a month.

## Related ADRs

[ADR-004](ADR-004-karma-ledger.md), [ADR-018](ADR-018-channel-agnostic-contributions.md), [ADR-036](ADR-036-rate-limiting.md)
