# ADR-004: Karma is an append-only ledger; the wallet is a projection

Status: Accepted (amended on 2026-11-21)
Date: 2026-11-21 (first accepted 2026-11-17)
Implementation status at dev 7fd66060: not started. Karma is a mutable counter in `wallet` plus rows in `karma_activity_log`, written from 13 places in the backend (for example `utils/karma.py` `add_karma`) and by the Discord bot.

## Context

A mutable karma counter written from many code paths has no history. It can't explain a balance,
can't make an award idempotent, and can't be reconciled. Awards arrive through retries,
duplicate reactions and replays, so the same event can be delivered more than once.

## Options considered

- **An append-only ledger as the source of truth,** with the wallet as a projection.
- **A mutable counter guarded by locks:** no history, and no idempotency across channels.
- **Event sourcing for the whole user aggregate:** far more machinery than awards need.

## Decision

- `contributions` owns `karma_ledger_entry`, an append-only table with
  `UNIQUE(source, source_ref)`.
  - Key columns use a binary (`ascii_bin`) collation, so keys never fold case or accents.
- **Keys:**
  - A submission is keyed by its channel reference, for example `discord:<message_id>` or
    `app:<client_request_id>`.
  - The first award for a submission reuses that key.
  - A re-award after a reversal is the next generation, `<key>#<n>`, computed under the
    submission row lock.
  - Reversals are keyed `reversal:<entry_id>`.
  - Keys are never per actor, so two appraisers can't create two awards.
- **Re-award is a legal state transition** (`REVERSED → APPROVED`). The state machine, together
  with the row lock, makes a replayed reaction a no-op.
- **Penalties:**
  - Karma may go negative, but only through `penalty` entries.
  - Coins are not part of this ledger. They live in `mucoin-service` ([ADR-054](ADR-054-mucoin-external-consumer.md)).
- **No hard deletes.** Removing a submission writes a reversal; entries are never updated or
  deleted.
- The wallet is updated atomically in the same transaction as the ledger entry.
- **Reconciliation:**
  - While each writer is being migrated, a reconciliation job compares the legacy log with the
    ledger and raises a ticket on drift.
  - After a module's cut-over, a nightly job compares each wallet with the sum of its ledger
    entries and pages on any drift.
  - Projections can be rebuilt from the ledger by command.
- Other modules award karma only through `modules.contributions.public`.

### Refinements (2026-11-21)

- Key and reference columns are `ascii_bin`, and the ledger is indexed on `submission_id`, which generation numbering reads under the submission lock.
- `appraise` carries the generation the caller means to approve (`expected_generation`). If the submission has already moved on, the call changes nothing, so a delayed approval cannot re-award after a reversal.
- Penalties and reversals are never refused because of the balance; only a negative adjustment stops at zero.
- `period` is the India Standard Time month, set before any backfill, because ledger rows are immutable.
- `karma_ledger_entry` is karma-only. `wallet.karma` is the sum of the karma ledger. `wallet.coin` and the other dormant coin tables are frozen: core neither reads nor writes them for new features ([ADR-054](ADR-054-mucoin-external-consumer.md)).
- `SubmissionApproved` gains `award_generation`, and `KarmaReversed` and `KarmaAdjusted` gain attribution and `period` fields. The fields are additive, so the versions don't change.

## Consequences

- Every balance can be explained, and every award takes effect once.
- One more table, plus a one-time opening-balance backfill.
- Deleting an account means anonymising it, not deleting rows ([ADR-052](ADR-052-privacy-minors-erasure.md)).

## Revisit when

- Awards exceed about 100 per second sustained. Then consider partitioning the ledger by month,
  with no inbound foreign keys.

## Related ADRs

[ADR-005](ADR-005-transactional-outbox.md), [ADR-018](ADR-018-channel-agnostic-contributions.md), [ADR-024](ADR-024-leaderboards-and-period-totals.md), [ADR-041](ADR-041-transactions-and-consistency.md), [ADR-052](ADR-052-privacy-minors-erasure.md)
