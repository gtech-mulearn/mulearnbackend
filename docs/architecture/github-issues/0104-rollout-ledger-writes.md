# Turn on ledger writes in production

| | |
|---|---|
| ID | 0104 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | S |
| Labels | arch, phase:4, module:contributions, type:chore, size:S, maintainer-only |
| Depends on | 0094, 0096, 0097, 0098, 0099, 0100 |
| Blocks | none |
| Repos | mulearnbackend |

## Why

With the writers moved and the backfill tooling ready, the ledger is turned on in production in steps, watched by reconciliation.

## Before you start

- Maintainer-only: it needs production access.
- Issues 0094, 0096, 0097, 0098, 0099 and 0100 must be merged.

## What to do

1. Off-peak, run `contributions_classify --dry-run` on production, then for real. Review collisions.
2. Run `contributions_backfill --dry-run`, then for real, with the load threshold set. Review negative opening entries.
3. Turn `contributions.ledger_writes` on for 10% of users. Watch reconciliation for 3 days, then turn it on for 100%.
4. Record every count and every drift explanation on the issue.

## Acceptance criteria

- [ ] Right after the backfill, reconciliation reports no drift except `unattributed` drift from the bot's direct writes.
- [ ] At 100%, reconciliation reports no `legacy` and no `unexplained` drift. The 14-day watch continues in the cut-over epic after this issue closes.
- [ ] The remaining `unattributed` drift traces back to the bot's direct writes, as expected until the cut-over.

## How to test

Record the reconciliation reports on the issue.

## Out of scope

- The bot switch and the revoke of its write grants (the cut-over epic).

## Notes for reviewers

Run outside caution windows. Keep the flag ready to turn off.
