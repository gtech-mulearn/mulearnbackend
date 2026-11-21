# Add opening balances and the award backfill

| | |
|---|---|
| ID | 0094 |
| Phase / milestone | Phase 4: Contributions and the ledger |
| Module | contributions |
| Size | L |
| Labels | arch, phase:4, module:contributions, type:feature, size:L, core-review |
| Depends on | 0085, 0093 |
| Blocks | 0100, 0104 |
| Repos | mulearnbackend |

## Why

The ledger must start out equal to today's balances: every user's ledger sum must equal `wallet.karma` before the ledger is trusted ([ADR-004](../adr/ADR-004-karma-ledger.md), [06-data-and-schema.md](../06-data-and-schema.md#the-karma-ledger)).

## Before you start

- Issues 0085 and 0093 must be merged.

## What to do

1. Create `modules/contributions/management/commands/contributions_backfill.py` (`--batch`, `--after-user-id`, `--dry-run` by default, `--max-threads-running`). For each user, in user-id batches:
   - create one `award` entry per classified approved row, keyed by its `source_ref`, with the row's karma and its IST period;
   - create one `opening` entry keyed `opening:<user_id>`, equal to `wallet.karma` minus the sum of the backfilled awards, so the ledger sum equals today's balance. Do each user in one transaction that first locks the user's wallet row (`select_for_update`), so a concurrent award can't land between the read and the write.
2. Before each batch, read `Threads_running`. If it is above the threshold, pause, and after 3 pauses abort cleanly.
3. Report the users processed, the entries created, and any user with a negative opening entry.
4. Make it idempotent: a second run creates nothing, because the keys already exist. Drift that appears after a user's opening exists is corrected by a true-up through `adjust` (issue 0086), never by changing the opening.

## Acceptance criteria

- [ ] After a run on the MySQL tier fixture, every user's ledger sum equals `wallet.karma`.
- [ ] A second run creates no entries.
- [ ] The dry run writes nothing.

## How to test

```sh
scripts/test.sh --mysql modules/contributions/tests/
```

These tests run on the MySQL tier. Mark each one `@pytest.mark.mysql` and `@pytest.mark.django_db`. Use `transaction=True` only when the test needs rows committed across connections (concurrency tests), and then create every row the test needs. `--mysql` runs only marked tests, against the schema already loaded into `test_mulearn` ([Test tiers](../12-testing-and-quality-gates.md#test-tiers)).

## Out of scope

- Running it on production (issue 0104).

## Notes for reviewers

Check that the opening entry formula makes the ledger sum equal `wallet.karma` exactly.
